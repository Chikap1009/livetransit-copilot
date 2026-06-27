"""LLM gateway: which model the agent uses, and usage limits to keep it safe.

Pydantic AI selects a provider by a single model string, so switching brains (the
Phase H fallback chain) is config, not code.
"""
import os

from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.usage import UsageLimits

# Error fragments that should trigger a fallback:
#  - rate limits / quota (429, resource_exhausted, quota)
#  - transient provider overload (503 / UNAVAILABLE / "overloaded" — Gemini's
#    "experiencing high demand, try again later"); these should fail over, not surface
#  - Groq's flaky streaming tool-call errors (usually succeed on the next provider)
_FALLBACK_MARKERS = (
    "429", "resource_exhausted", "quota",
    "503", "unavailable", "overloaded", "high demand", "try again later",
    "failed to call a function", "failed_generation", "tool_use_failed",
)


def _should_fallback(exc: Exception) -> bool:
    """Trigger fallback on rate-limit/quota/transient tool errors from ANY provider.

    The non-streaming path wraps errors as ModelAPIError, but the streaming path can
    raise a provider's raw error (e.g. Google's ClientError 429 or Groq's APIError), so
    we also match by message — otherwise the chat (which streams) never falls over.
    """
    if isinstance(exc, ModelAPIError):
        return True
    text = str(exc).lower()
    return any(marker in text for marker in _FALLBACK_MARKERS)


# Fallback chain (config, not code). Gemini is the only free provider that reliably
# emits well-formed tool calls; Groq's Llama intermittently emits them as <function=...>
# *text* that can't be parsed, so it sits LAST as a plain-text safety net.
#
# We chain MULTIPLE Gemini keys: each key (a different Google project/account) has its
# OWN daily free quota, so when one key's Flash + Flash-Lite are exhausted we fall to the
# NEXT key's Gemini — staying on a reliable provider instead of dropping to Groq. The
# first key (GEMINI_API_KEY) is the priority; GEMINI_API_KEY_2, _3, ... are backups.
# A 429 from an exhausted key fails over instantly (no quota consumed), so a temporarily
# spent priority key costs nothing and resumes automatically when it resets.
_GEMINI_MODELS = ("gemini-2.5-flash", "gemini-2.5-flash-lite")
_GROQ = "groq:llama-3.3-70b-versatile"


def _gemini_keys() -> list[str]:
    """GEMINI_API_KEY (priority) then GEMINI_API_KEY_2, _3, ... (backups), in order."""
    keys = []
    if primary := os.environ.get("GEMINI_API_KEY"):
        keys.append(primary)
    i = 2
    while key := os.environ.get(f"GEMINI_API_KEY_{i}"):
        keys.append(key)
        i += 1
    return keys


def _build_chain() -> list:
    models: list = []
    for key in _gemini_keys():
        provider = GoogleProvider(api_key=key)
        models.extend(GoogleModel(name, provider=provider) for name in _GEMINI_MODELS)
    models.append(_GROQ)   # last-resort plain-text safety net
    return models


MODEL = FallbackModel(*_build_chain(), fallback_on=_should_fallback)

# Cap model requests per question so a runaway ReAct loop can't burn the quota.
# Higher than the default to allow for fallback attempts across the multi-key chain.
USAGE_LIMITS = UsageLimits(request_limit=12)

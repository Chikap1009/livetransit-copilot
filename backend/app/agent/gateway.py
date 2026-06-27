"""LLM gateway: which model the agent uses, and usage limits to keep it safe.

Pydantic AI selects a provider by a single model string, so switching brains (the
Phase H fallback chain) is config, not code.
"""
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.fallback import FallbackModel
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


# Fallback chain (config, not code). Both Gemini tiers emit well-formed structured
# tool calls; Groq's Llama intermittently emits tool calls as <function=...> *text*
# that can't be parsed, so it sits LAST as a plain-text safety net. Flash-Lite has its
# own (larger) free quota, so when Flash's 250/day is exhausted we fall to another
# reliable Gemini tier before ever touching Groq. Add Cerebras/OpenRouter here in Phase H.
_FLASH = "google:gemini-2.5-flash"
_FLASH_LITE = "google:gemini-2.5-flash-lite"
_GROQ = "groq:llama-3.3-70b-versatile"
MODEL = FallbackModel(
    _FLASH,
    _FLASH_LITE,
    _GROQ, _GROQ,
    fallback_on=_should_fallback,
)

# Cap model requests per question so a runaway ReAct loop can't burn the quota.
USAGE_LIMITS = UsageLimits(request_limit=8)

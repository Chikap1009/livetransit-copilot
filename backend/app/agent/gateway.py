"""LLM gateway: which model the agent uses, and usage limits to keep it safe.

Pydantic AI selects a provider by a single model string, so switching brains (the
Phase H fallback chain) is config, not code.
"""
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.usage import UsageLimits


# Error fragments that should trigger a fallback (rate limits, plus Groq's flaky
# streaming tool-call error which is transient and usually succeeds on retry).
_FALLBACK_MARKERS = (
    "429", "resource_exhausted", "quota",
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


# Fallback chain: Gemini first; on rate-limit, fall to Groq. Groq's streaming tool-call
# is intermittently flaky, so it's listed multiple times for in-place retries. Provider
# switch is pure config — add Cerebras/OpenRouter here later (Phase H).
_GROQ = "groq:llama-3.3-70b-versatile"
MODEL = FallbackModel(
    "google:gemini-2.5-flash",
    _GROQ, _GROQ, _GROQ, _GROQ,
    fallback_on=_should_fallback,
)

# Cap model requests per question so a runaway ReAct loop can't burn the quota.
USAGE_LIMITS = UsageLimits(request_limit=8)

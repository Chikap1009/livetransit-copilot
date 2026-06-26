"""LLM gateway: which model the agent uses, and usage limits to keep it safe.

Pydantic AI selects a provider by a single model string, so switching brains (the
Phase H fallback chain) is config, not code.
"""
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.usage import UsageLimits

# Fallback chain: try Gemini first; on failure (e.g. 429 rate-limit) automatically
# retry on Groq with the same tools/context. Provider switch is config, not code —
# add Cerebras/OpenRouter here later (Phase H).
MODEL = FallbackModel(
    "google:gemini-2.5-flash",
    "groq:llama-3.3-70b-versatile",
)

# Cap model requests per question so a runaway ReAct loop can't burn the quota.
USAGE_LIMITS = UsageLimits(request_limit=8)

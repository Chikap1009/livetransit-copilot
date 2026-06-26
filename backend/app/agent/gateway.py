"""LLM gateway: which model the agent uses, and usage limits to keep it safe.

Pydantic AI selects a provider by a single model string, so switching brains (the
Phase H fallback chain) is config, not code.
"""
from pydantic_ai.usage import UsageLimits

# Primary brain: Google Gemini 2.5 Flash (free tier, supports tool calling).
MODEL = "google:gemini-2.5-flash"

# Cap model requests per question so a runaway ReAct loop can't burn the quota.
USAGE_LIMITS = UsageLimits(request_limit=8)

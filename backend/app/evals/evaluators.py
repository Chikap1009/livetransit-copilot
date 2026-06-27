"""Deterministic evaluators for the eval harness (Phase G).

Kept free of any LLM/gateway import so they can be unit-tested in CI (which has no
API keys) without building the model chain.
"""
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class ExpectedTools(Evaluator):
    """Trajectory: did the run call the tool(s) the case expects?"""

    def evaluate(self, ctx: EvaluatorContext) -> dict:
        expected = (ctx.metadata or {}).get("expected_tools")
        if not expected:
            return {}
        used = set(ctx.output.get("tools_used", []))
        return {"expected_tools": all(t in used for t in expected)}


@dataclass
class AnswerContains(Evaluator):
    """Final answer: does it include the expected stable fact(s)?"""

    def evaluate(self, ctx: EvaluatorContext) -> dict:
        needles = (ctx.metadata or {}).get("contains")
        if not needles:
            return {}
        hay = (ctx.output.get("answer") or "").lower()
        return {"answer_contains": all(n.lower() in hay for n in needles)}


@dataclass
class NoError(Evaluator):
    """The run produced an answer and didn't error out."""

    def evaluate(self, ctx: EvaluatorContext) -> dict:
        ans = ctx.output.get("answer") or ""
        return {"answered": bool(ans) and not ans.startswith("ERROR:")}

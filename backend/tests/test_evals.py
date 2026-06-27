"""Deterministic tests of the eval evaluators (Phase G) — no LLM, CI-safe.

Proves the harness *catches regressions*: a good agent output passes the checks,
a broken one fails them. This is the "a deliberately broken change drops the score"
guarantee, verified without spending any LLM quota.
"""
from pydantic_evals.evaluators import EvaluatorContext

from backend.app.evals.cases import AnswerContains, ExpectedTools, NoError


def _ctx(metadata: dict, output: dict) -> EvaluatorContext:
    return EvaluatorContext(
        name="case", inputs="q", metadata=metadata, expected_output=None,
        output=output, duration=0.0, _span_tree=None, attributes={}, metrics={},
    )


def test_expected_tools_trajectory():
    meta = {"expected_tools": ["search_docs"]}
    good = ExpectedTools().evaluate(_ctx(meta, {"tools_used": ["search_docs"], "answer": "x"}))
    broken = ExpectedTools().evaluate(_ctx(meta, {"tools_used": ["get_weather"], "answer": "x"}))
    assert good["expected_tools"] is True
    assert broken["expected_tools"] is False


def test_answer_contains_fact():
    meta = {"contains": ["2.40"]}
    good = AnswerContains().evaluate(_ctx(meta, {"answer": "The fare is $2.40.", "tools_used": []}))
    broken = AnswerContains().evaluate(_ctx(meta, {"answer": "I'm not sure.", "tools_used": []}))
    assert good["answer_contains"] is True
    assert broken["answer_contains"] is False


def test_no_error_flags_failures():
    good = NoError().evaluate(_ctx({}, {"answer": "Here you go.", "tools_used": []}))
    broken = NoError().evaluate(_ctx({}, {"answer": "ERROR: quota exhausted", "tools_used": []}))
    assert good["answered"] is True
    assert broken["answered"] is False

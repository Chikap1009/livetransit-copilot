"""The golden set + evaluators for the Copilot (Phase G).

Each Case is a question plus expected behaviour in metadata:
  * expected_tools — the tool(s) a correct run should call (TRAJECTORY check),
  * contains       — substrings a correct ANSWER should include (stable facts only).
A few open-ended cases also carry an LLMJudge for answer QUALITY.

We deliberately avoid asserting live numbers (positions/arrivals change); trajectory
and stable-fact checks are the robust signal.
"""
from dataclasses import dataclass

from pydantic_evals import Case
from pydantic_evals.evaluators import Evaluator, EvaluatorContext, LLMJudge

from backend.app.agent.gateway import MODEL


# --- custom evaluators -------------------------------------------------------
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


# Quality judge for open-ended cases (kept to a few cases to bound token use).
_QUALITY = LLMJudge(
    rubric=(
        "The answer accurately, relevantly, and helpfully addresses the rider's MBTA question. "
        "It should be grounded (not invented) and directly useful. Score true only if a Boston "
        "transit rider would find it correct and helpful."
    ),
    model=MODEL,
    include_input=True,
)


def _c(name, question, *, tools=None, contains=None, judge=False, category="") -> Case:
    meta = {"category": category}
    if tools:
        meta["expected_tools"] = tools
    if contains:
        meta["contains"] = contains
    return Case(
        name=name,
        inputs=question,
        metadata=meta,
        evaluators=(_QUALITY,) if judge else (),
    )


# --- the golden set ----------------------------------------------------------
GOLDEN: list[Case] = [
    # positions
    _c("pos_red", "Where are the Red Line trains right now?",
       tools=["get_vehicle_positions"], category="positions"),
    _c("pos_bus66", "Where are the buses on route 66?",
       tools=["get_vehicle_positions"], category="positions"),
    _c("pos_bus77", "Is bus route 77 running right now?",
       tools=["get_vehicle_positions"], category="positions"),
    # arrivals / ETA
    _c("eta_stop", "What are the predicted arrivals at stop 70061?",
       tools=["predict_eta"], category="arrivals"),
    # alerts
    _c("alerts_orange", "Are there any service alerts on the Orange Line?",
       tools=["get_service_alerts"], category="alerts"),
    # trip planning — direct
    _c("trip_direct", "How do I get from Kendall to Park Street?",
       tools=["plan_trip"], contains=["red"], judge=True, category="trip"),
    _c("trip_davis_alewife", "Plan a trip from Davis to Alewife.",
       tools=["plan_trip"], contains=["red"], category="trip"),
    # trip planning — transfer
    _c("trip_transfer", "How do I get from Kendall to Boylston?",
       tools=["plan_trip"], contains=["park street"], judge=True, category="trip"),
    _c("trip_harvard_airport", "What's the best way from Harvard to the Airport?",
       tools=["plan_trip"], judge=True, category="trip"),
    # RAG / policy
    _c("rag_fare", "How much is a subway fare?",
       tools=["search_docs"], contains=["2.40"], category="rag"),
    _c("rag_monthly", "How much is a monthly LinkPass?",
       tools=["search_docs"], contains=["90"], category="rag"),
    _c("rag_bike", "Can I bring my full-size bike on the Red Line during rush hour?",
       tools=["search_docs"], contains=["folding"], judge=True, category="rag"),
    _c("rag_elevator", "What happens if the elevator at my station is broken?",
       tools=["search_docs"], contains=["shuttle"], judge=True, category="rag"),
    _c("rag_overnight", "Are there overnight subway trains after 2am?",
       tools=["search_docs"], category="rag"),
    _c("rag_transfer_free", "Does my CharlieCard give me free transfers?",
       tools=["search_docs"], contains=["two hours"], category="rag"),
    _c("rag_accessible", "Is the Green Line wheelchair accessible?",
       tools=["search_docs"], category="rag"),
    # memory
    _c("mem_write_home", "Remember that my home stop is Davis.",
       tools=["remember"], category="memory"),
    _c("mem_write_pref", "Just so you know, I prefer fewer transfers.",
       tools=["remember"], category="memory"),
    _c("mem_read_home", "What's my home stop?",
       tools=["recall"], contains=["davis"], category="memory"),
    # watchdog delegation
    _c("watchdog_route", "Have the watchdog investigate route 1 for problems.",
       tools=["investigate_route"], category="watchdog"),
    _c("watchdog_red", "Can you check the health of the Red Line?",
       tools=["investigate_route"], category="watchdog"),
    # edge cases (graceful, no crash)
    _c("edge_offtopic", "What's the airspeed velocity of an unladen swallow?",
       category="edge"),
    _c("edge_joke", "Tell me a joke about elephants.", category="edge"),
    _c("edge_nonsense_stop", "When is the next train at the North Pole station?",
       category="edge"),
]

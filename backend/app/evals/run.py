"""Run the agent eval harness.

    python -m backend.app.evals.run          # full golden set
    python -m backend.app.evals.run 3        # smoke test: first 3 cases

Runs each golden case through the live Copilot, then scores trajectory
(expected tools), stable-fact answer checks, and answer quality (LLMJudge).
"""
import sys

from psycopg_pool import AsyncConnectionPool
from pydantic_ai.messages import ToolCallPart

from backend.app.core import config  # noqa: F401  (imported first to load .env keys)
from backend.app.core.asyncrun import run as run_loop

# The report table uses Unicode (✔/✗); make the Windows console accept it.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

_pool: AsyncConnectionPool | None = None


async def task(question: str) -> dict:
    """Run the Copilot on one question; return its answer text + tools used."""
    # Imported lazily so .env is loaded (via config) before the gateway builds.
    from backend.app.agent.copilot import Deps, copilot
    from backend.app.agent.gateway import USAGE_LIMITS

    try:
        result = await copilot.run(
            question, deps=Deps(pool=_pool, user_id="demo"), usage_limits=USAGE_LIMITS,
        )
    except Exception as exc:
        return {"answer": f"ERROR: {type(exc).__name__}: {exc}", "tools_used": []}

    out = result.output
    answer = getattr(out, "summary", None) or str(out)
    facts = " ".join(getattr(out, "facts", []) or [])
    sources = " ".join(getattr(out, "sources", []) or [])
    tools_used = [
        p.tool_name
        for m in result.all_messages()
        for p in getattr(m, "parts", [])
        if isinstance(p, ToolCallPart) and not p.tool_name.startswith("final_result")
    ]
    return {"answer": f"{answer} | {facts} | {sources}", "tools_used": tools_used}


async def main():
    global _pool
    from pydantic_evals import Dataset

    from backend.app.evals.cases import GOLDEN, AnswerContains, ExpectedTools, NoError

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    cases = GOLDEN[:limit] if limit else GOLDEN

    _pool = AsyncConnectionPool(config.DATABASE_URL, min_size=1, max_size=4, open=False)
    await _pool.open()
    try:
        dataset = Dataset(
            name="copilot-golden",
            cases=cases,
            evaluators=[ExpectedTools(), AnswerContains(), NoError()],
        )
        report = await dataset.evaluate(task, max_concurrency=3)
        report.print(include_input=True, include_output=False)
    finally:
        await _pool.close()


if __name__ == "__main__":
    run_loop(main())

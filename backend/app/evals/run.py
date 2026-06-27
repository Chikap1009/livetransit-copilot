"""Run the agent eval harness.

    python -m backend.app.evals.run            # full golden set (resumes from saved progress)
    python -m backend.app.evals.run 3          # smoke test: first 3 cases
    python -m backend.app.evals.run --fresh    # ignore saved progress, start over
    EVAL_JUDGE=1 python -m backend.app.evals.run   # also run the LLM quality judge

Runs each golden case through the live Copilot, then scores trajectory (expected
tools), stable-fact answer checks, and (opt-in) answer quality.

CHECKPOINTING: each case's result is saved to _progress.json as it succeeds, so if a
run dies partway (e.g. free-tier quota exhausted) the next run reuses the done cases and
only re-runs the missing/errored ones. Delete the file or pass --fresh to start over.
"""
import hashlib
import json
import sys
from pathlib import Path

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
_PROGRESS_PATH = Path(__file__).parent / "_progress.json"
_progress: dict = {}


def _key(question: str) -> str:
    return hashlib.sha256(question.encode()).hexdigest()[:16]


def _load_progress() -> dict:
    if _PROGRESS_PATH.exists():
        return json.loads(_PROGRESS_PATH.read_text(encoding="utf-8"))
    return {}


def _save_progress() -> None:
    _PROGRESS_PATH.write_text(json.dumps(_progress, indent=2), encoding="utf-8")


async def task(question: str) -> dict:
    """Run the Copilot on one question; return its answer text + tools used.

    Reuses a previously-saved successful result for this question (checkpointing).
    """
    key = _key(question)
    if key in _progress:
        return _progress[key]

    # Imported lazily so .env is loaded (via config) before the gateway builds.
    from backend.app.agent.copilot import Deps, copilot
    from backend.app.agent.gateway import USAGE_LIMITS

    try:
        result = await copilot.run(
            question, deps=Deps(pool=_pool, user_id="demo"), usage_limits=USAGE_LIMITS,
        )
    except Exception as exc:
        # Don't checkpoint errors — they should be retried on the next run.
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
    output = {"answer": f"{answer} | {facts} | {sources}", "tools_used": tools_used}
    _progress[key] = output           # checkpoint this success immediately
    _save_progress()
    return output


async def main():
    global _pool, _progress
    from pydantic_evals import Dataset

    from backend.app.evals.cases import GOLDEN
    from backend.app.evals.evaluators import AnswerContains, ExpectedTools, NoError

    args = sys.argv[1:]
    fresh = "--fresh" in args
    if fresh and _PROGRESS_PATH.exists():
        _PROGRESS_PATH.unlink()
    nums = [int(a) for a in args if a.isdigit()]
    limit = nums[0] if nums else None
    cases = GOLDEN[:limit] if limit else GOLDEN

    _progress = _load_progress()
    done = sum(1 for c in cases if _key(c.inputs) in _progress)
    print(f"Resuming: {done}/{len(cases)} cases already saved; running the rest.")

    _pool = AsyncConnectionPool(config.DATABASE_URL, min_size=1, max_size=4, open=False)
    await _pool.open()
    try:
        dataset = Dataset(
            name="copilot-golden",
            cases=cases,
            evaluators=[ExpectedTools(), AnswerContains(), NoError()],
        )
        # Serial: free Gemini is 10 requests/min/model, and with the priority keys
        # exhausted everything funnels onto the fresh key — concurrency bursts blow the
        # rate limit. One at a time keeps us under it.
        report = await dataset.evaluate(task, max_concurrency=1)
        report.print(include_input=True, include_output=False)
        saved = sum(1 for c in cases if _key(c.inputs) in _progress)
        print(f"Progress saved: {saved}/{len(cases)} cases. Re-run later to finish the rest.")
    finally:
        await _pool.close()


if __name__ == "__main__":
    run_loop(main())

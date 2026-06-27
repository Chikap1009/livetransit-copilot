"""The Network Watchdog: a second, autonomous agent (Phase F).

Nobody chats with the Watchdog. Cheap SQL detection (anomalies.py) finds candidate
problems on the live feed; for each genuine one the Watchdog *investigates* (it can
check service alerts and the weather) and writes a structured IncidentReport, stored
in `incidents`. The Copilot (supervisor) can also delegate an investigation to it
(supervisor/worker multi-agent pattern).

Token use is bounded: detection is free, only a capped number of fresh anomalies per
run reach the LLM, and the agent has a tight request limit.
"""
import json
from dataclasses import dataclass

from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from backend.app.agent import anomalies, tools
from backend.app.agent.gateway import MODEL
from backend.app.agent.schemas import IncidentReport


@dataclass
class WatchdogDeps:
    pool: AsyncConnectionPool


WATCHDOG_PROMPT = (
    "You are the LiveTransit Network Watchdog, monitoring the MBTA (Boston) for problems. "
    "You are given ONE detected anomaly with its evidence. Investigate it: you may call "
    "get_service_alerts (to see if the agency already reports an issue on the route) and "
    "get_weather (to judge if conditions explain delays). Then write a concise IncidentReport: "
    "set a sensible severity, summarize what's happening for a rider, and give the most likely "
    "cause from the evidence. Be measured — bunching of two buses for a minute is 'low'; a line "
    "with no service or a 40-minute delay is 'high'. Never invent data beyond the evidence/tools."
)

watchdog = Agent(
    MODEL,
    deps_type=WatchdogDeps,
    output_type=IncidentReport,
    system_prompt=WATCHDOG_PROMPT,
)

# Tight cap — the Watchdog runs often and should sip, not gulp.
WATCHDOG_LIMITS = UsageLimits(request_limit=4)


@watchdog.tool
async def get_service_alerts(ctx: RunContext[WatchdogDeps], route: str | None = None) -> dict:
    """Current MBTA service alerts, optionally filtered to a route."""
    return await tools.get_service_alerts(route)


@watchdog.tool
async def get_weather(ctx: RunContext[WatchdogDeps]) -> dict:
    """Current Boston weather, to judge whether conditions explain delays."""
    return await tools.get_weather()


async def investigate(pool: AsyncConnectionPool, anomaly: dict) -> IncidentReport:
    """Run the Watchdog agent on one anomaly and return its report."""
    prompt = (
        "Investigate this detected anomaly and write the incident report:\n"
        f"{json.dumps(anomaly)}"
    )
    result = await watchdog.run(
        prompt, deps=WatchdogDeps(pool=pool), usage_limits=WATCHDOG_LIMITS,
    )
    return result.output


async def _recent_exists(pool: AsyncConnectionPool, anomaly: dict, minutes: int = 20) -> bool:
    """True if we already logged this kind/route/fingerprint recently (avoid spam)."""
    sql = """
        SELECT 1 FROM incidents
        WHERE kind = %s AND route_id IS NOT DISTINCT FROM %s
          AND fingerprint = %s AND created_at >= now() - make_interval(mins => %s)
        LIMIT 1
    """
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(sql, (anomaly["kind"], anomaly["route_id"],
                                anomaly["fingerprint"], minutes))
        return await cur.fetchone() is not None


async def _store(pool: AsyncConnectionPool, anomaly: dict, report: IncidentReport) -> int:
    sql = """
        INSERT INTO incidents (kind, route_id, severity, summary, evidence, fingerprint)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(sql, (
            report.kind, report.route_id or anomaly["route_id"], report.severity,
            f"{report.summary} (Likely cause: {report.likely_cause})",
            Json(anomaly["evidence"]), anomaly["fingerprint"],
        ))
        return (await cur.fetchone())[0]


async def run_once(pool: AsyncConnectionPool, max_incidents: int = 3) -> list[dict]:
    """Detect anomalies and investigate up to max_incidents fresh ones (LLM-bounded)."""
    created = []
    for anomaly in await anomalies.detect(pool):
        if len(created) >= max_incidents:
            break
        if await _recent_exists(pool, anomaly):
            continue
        report = await investigate(pool, anomaly)
        incident_id = await _store(pool, anomaly, report)
        created.append({"id": incident_id, "kind": report.kind, "route_id": report.route_id,
                        "severity": report.severity, "summary": report.summary})
    return created

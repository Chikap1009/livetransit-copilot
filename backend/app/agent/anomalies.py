"""Cheap anomaly detection over the live feed (Phase F, no LLM).

Generates candidate anomalies the Watchdog then investigates. Three kinds:
  * bunching — two same-route vehicles too close together (the classic),
  * delay    — a running trip arriving well behind schedule,
  * gap      — a rapid-transit line with no vehicles during service hours.

Detection is intentionally cheap and a bit permissive; the Watchdog (LLM) judges
severity and writes the report, so a few soft candidates here are fine.
"""
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

BUNCHING_METERS = 200          # same-route vehicles closer than this = candidate bunching
DELAY_SECONDS = 600            # a running trip >10 min late
RAIL_LINES = ("Red", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E")


async def _bunching(pool: AsyncConnectionPool) -> list[dict]:
    # Buses only (route_type 3): the classic bunching case. Rail "bunching" is mostly
    # coupled cars or trains stacked at terminals — noise we deliberately exclude.
    sql = f"""
        WITH latest AS (
            SELECT DISTINCT ON (vp.vehicle_id) vp.vehicle_id, vp.route_id, vp.geom
            FROM vehicle_positions vp
            JOIN routes r ON r.route_id = vp.route_id AND r.route_type = 3
            WHERE vp.recorded_at >= now() - interval '90 seconds'
            ORDER BY vp.vehicle_id, vp.recorded_at DESC
        ),
        pairs AS (
            SELECT a.route_id, a.vehicle_id AS v1, b.vehicle_id AS v2,
                   ST_Distance(a.geom::geography, b.geom::geography) AS meters
            FROM latest a
            JOIN latest b ON a.route_id = b.route_id AND a.vehicle_id < b.vehicle_id
            WHERE ST_DWithin(a.geom::geography, b.geom::geography, {BUNCHING_METERS})
        ),
        ranked AS (
            SELECT *, row_number() OVER (PARTITION BY route_id ORDER BY meters) AS rn FROM pairs
        )
        SELECT route_id, v1, v2, round(meters) AS meters
        FROM ranked WHERE rn = 1            -- closest pair per route only
        ORDER BY meters LIMIT 8
    """
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql)
        rows = await cur.fetchall()
    return [
        {
            "kind": "bunching", "route_id": r["route_id"],
            "fingerprint": f"{r['route_id']}:{r['v1']}:{r['v2']}",
            "evidence": {"vehicles": [r["v1"], r["v2"]], "meters": int(r["meters"])},
        }
        for r in rows
    ]


async def _delays(pool: AsyncConnectionPool) -> list[dict]:
    sql = f"""
        SELECT route_id, trip_id, max(delay_seconds) AS max_delay
        FROM vehicle_arrivals
        WHERE service_date = (now() AT TIME ZONE 'America/New_York')::date
          AND arrived_at >= now() - interval '20 minutes'
        GROUP BY route_id, trip_id
        HAVING max(delay_seconds) > {DELAY_SECONDS}
        ORDER BY max_delay DESC
        LIMIT 5
    """
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql)
        rows = await cur.fetchall()
    return [
        {
            "kind": "delay", "route_id": r["route_id"],
            "fingerprint": f"{r['route_id']}:{r['trip_id']}",
            "evidence": {"trip_id": r["trip_id"], "delay_minutes": round(r["max_delay"] / 60)},
        }
        for r in rows
    ]


async def _gaps(pool: AsyncConnectionPool) -> list[dict]:
    # Only during service hours (NY 6:00–22:59); off-hours a gap is expected.
    sql = """
        WITH active AS (
            SELECT DISTINCT route_id FROM vehicle_positions
            WHERE recorded_at >= now() - interval '120 seconds'
        )
        SELECT line FROM unnest(%s::text[]) AS line
        WHERE EXTRACT(hour FROM now() AT TIME ZONE 'America/New_York') BETWEEN 6 AND 22
          AND line NOT IN (SELECT route_id FROM active)
    """
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, (list(RAIL_LINES),))
        rows = await cur.fetchall()
    return [
        {
            "kind": "gap", "route_id": r["line"], "fingerprint": f"{r['line']}:gap",
            "evidence": {"line": r["line"], "note": "no vehicles reporting in the last 2 minutes"},
        }
        for r in rows
    ]


async def detect(pool: AsyncConnectionPool) -> list[dict]:
    """All current anomaly candidates (cheap; no LLM)."""
    return await _bunching(pool) + await _delays(pool) + await _gaps(pool)

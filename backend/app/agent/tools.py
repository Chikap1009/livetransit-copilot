"""The agent's tools: thin async functions over the live body (DB + MBTA feeds).

The agent reasons; these do the real work. All read-only in Phase A.
"""
import httpx
from google.transit import gtfs_realtime_pb2
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.agent import rag, routing
from backend.app.ml import predictor

MBTA_ALERTS_URL = "https://cdn.mbta.com/realtime/Alerts.pb"
RECENT = "90 seconds"


async def get_vehicle_positions(pool: AsyncConnectionPool, route: str, limit: int = 25) -> dict:
    """Latest position of each vehicle currently running a route."""
    sql = f"""
        SELECT DISTINCT ON (vehicle_id) vehicle_id, route_id,
               round(latitude::numeric, 5) AS lat, round(longitude::numeric, 5) AS lon
        FROM vehicle_positions
        WHERE route_id = %s AND recorded_at >= now() - interval '{RECENT}'
        ORDER BY vehicle_id, recorded_at DESC
        LIMIT %s
    """
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, (route, limit))
        rows = await cur.fetchall()
    return {"route": route, "count": len(rows), "vehicles": rows}


async def predict_eta(pool: AsyncConnectionPool, stop_id: str) -> dict:
    """Predicted upcoming arrivals (with delays) at a stop, via the LightGBM model."""
    sql = """
        WITH active AS (
            SELECT trip_id, route_id, max(stop_sequence) AS cur_seq,
                   (array_agg(delay_seconds ORDER BY stop_sequence DESC))[1] AS current_delay
            FROM vehicle_arrivals
            WHERE service_date = (now() AT TIME ZONE 'America/New_York')::date
            GROUP BY trip_id, route_id
            HAVING max(arrived_at) >= now() - interval '30 minutes'   -- still running
        ),
        cand AS (
            SELECT a.trip_id, a.route_id, a.current_delay, st.stop_sequence,
                   (((now() AT TIME ZONE 'America/New_York')::date::timestamp
                     AT TIME ZONE 'America/New_York') + st.arrival_time::interval) AS scheduled_ts
            FROM active a
            JOIN stop_times st
              ON st.trip_id = a.trip_id AND st.stop_id = %s AND st.arrival_time <> ''
            WHERE st.stop_sequence > a.cur_seq AND abs(a.current_delay) <= 1800
        )
        SELECT route_id, current_delay, stop_sequence, scheduled_ts,
               EXTRACT(hour FROM scheduled_ts AT TIME ZONE 'America/New_York')::int AS hour,
               EXTRACT(dow  FROM scheduled_ts AT TIME ZONE 'America/New_York')::int AS dow
        FROM cand
        WHERE scheduled_ts >= now() - interval '2 minutes'           -- future arrivals only
        ORDER BY scheduled_ts LIMIT 6
    """
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, (stop_id,))
        rows = await cur.fetchall()
    for r in rows:
        r["current_delay"] = float(r["current_delay"] or 0)
    preds = predictor.predict_delays(rows) if predictor.is_loaded() else [None] * len(rows)
    arrivals = [
        {
            "route": r["route_id"],
            "scheduled": r["scheduled_ts"].isoformat(),
            "predicted_delay_s": round(d) if d is not None else None,
        }
        for r, d in zip(rows, preds)
    ]
    return {"stop_id": stop_id, "count": len(arrivals), "arrivals": arrivals}


async def plan_trip(pool: AsyncConnectionPool, origin: str, destination: str) -> dict:
    """Plan a trip between two stops by name (direct trip, or rail transfers)."""
    return await routing.plan_trip(pool, origin, destination)


async def search_docs(pool: AsyncConnectionPool, query: str) -> dict:
    """Search MBTA alerts + policy/reference docs for passages relevant to a query."""
    return await rag.corrective_retrieve(pool, query)


async def get_service_alerts(route: str | None = None) -> dict:
    """Current MBTA service alerts, optionally filtered to a route."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(MBTA_ALERTS_URL, timeout=15)
        resp.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)
    alerts = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        alert = entity.alert
        routes = sorted({ie.route_id for ie in alert.informed_entity if ie.route_id})
        if route and route not in routes:
            continue
        header = alert.header_text.translation[0].text if alert.header_text.translation else ""
        alerts.append({"routes": routes, "header": header})
    return {"route": route, "count": len(alerts), "alerts": alerts[:15]}

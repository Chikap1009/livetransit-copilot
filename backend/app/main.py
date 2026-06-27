"""FastAPI app: REST endpoints over the live transit data."""
import asyncio
import hashlib
import json
import sys
import time
from contextlib import asynccontextmanager
from datetime import timedelta

import redis.asyncio as redis
from fastapi import FastAPI, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel
from pydantic_ai.messages import ToolCallPart

from backend.app.agent import conversation, rag, watchdog
from backend.app.agent.copilot import Deps, copilot
from backend.app.agent.gateway import USAGE_LIMITS
from backend.app.core import config, metrics
from backend.app.ml import predictor

DEMO_USER = "demo"   # single-user demo; real per-user ids arrive with auth (Phase J)

# How recent a position must be to count as a vehicle's "current" location.
RECENT_WINDOW = "90 seconds"
BROADCAST_INTERVAL = 2  # seconds between live pushes to all WebSocket clients

pool: AsyncConnectionPool | None = None
rds: redis.Redis | None = None

# Currently-connected live-map clients. ONE DB read per tick is pushed to all of
# them — that single-read-serves-everyone is the "fan-out".
clients: set[WebSocket] = set()

LIVE_SQL = f"""
    SELECT DISTINCT ON (vehicle_id)
        vehicle_id, route_id, latitude AS lat, longitude AS lon, bearing
    FROM vehicle_positions
    WHERE recorded_at >= now() - interval '{RECENT_WINDOW}'
    ORDER BY vehicle_id, recorded_at DESC
"""


async def broadcaster():
    """Every BROADCAST_INTERVAL: one DB read, pushed to every connected client."""
    while True:
        await asyncio.sleep(BROADCAST_INTERVAL)
        if not clients:
            continue
        try:
            rows = await fetch(LIVE_SQL, ())
        except Exception:
            continue
        payload = json.dumps({"type": "positions", "vehicles": rows}, default=str)
        for ws in list(clients):
            try:
                await ws.send_text(payload)
            except Exception:
                clients.discard(ws)  # prune dead connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the DB pool + Redis client and start the broadcaster at startup."""
    global pool, rds
    pool = AsyncConnectionPool(config.DATABASE_URL, min_size=1, max_size=5, open=False)
    await pool.open()
    rds = redis.from_url(config.REDIS_URL, decode_responses=True)
    try:
        predictor.load()  # ETA model (optional: endpoint degrades gracefully if absent)
    except Exception as exc:
        print(f"ETA model not loaded: {exc}")
    task = asyncio.create_task(broadcaster())
    rag_task = asyncio.create_task(_refresh_rag())  # populate/refresh RAG library (non-blocking)
    bg = [task, rag_task]
    if config.WATCHDOG_ENABLED:
        bg.append(asyncio.create_task(_watchdog_loop()))
    yield
    for t in bg:
        t.cancel()
    await rds.aclose()
    await pool.close()


async def _refresh_rag():
    """Ingest policy docs + live alerts in the background so startup isn't blocked."""
    try:
        counts = await rag.bootstrap(pool)
        print(f"RAG library ingested: {counts}")
    except Exception as exc:
        print(f"RAG ingestion skipped: {exc}")


async def _watchdog_loop():
    """Periodically run the Network Watchdog (only when WATCHDOG_ENABLED)."""
    while True:
        await asyncio.sleep(config.WATCHDOG_INTERVAL_SECONDS)
        try:
            created = await watchdog.run_once(pool)
            if created:
                print(f"Watchdog logged {len(created)} incident(s)")
        except Exception as exc:
            print(f"Watchdog run failed: {exc}")


app = FastAPI(title="LiveTransit API", lifespan=lifespan)

# Allow the Next.js dev frontend (a different origin) to call the API/SSE.
# Dev-permissive; tighten to specific origins in production (Phase J).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the minimal live-map page at /web (same origin as the API -> no CORS for the WS).
app.mount("/web", StaticFiles(directory="frontend", html=True), name="web")


@app.middleware("http")
async def track_latency(request: Request, call_next):
    """Record request latency, labeled by the ROUTE TEMPLATE (low cardinality)."""
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    label = getattr(route, "path", "unmatched")  # e.g. /stops/{stop_id}/arrivals, not the real id
    metrics.REQ_LATENCY.labels(request.method, label).observe(time.perf_counter() - start)
    return response


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus scrape endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class AskRequest(BaseModel):
    question: str
    thread_id: str | None = None   # pass to get conversation memory (Redis-backed)


# Phase H (pulled forward): short-TTL answer cache so repeated questions don't re-hit
# the LLM (saves scarce free-tier quota). Short TTL bounds staleness for live-data answers.
AGENT_CACHE_TTL = 90


def _answer_cache_key(user_id: str, question: str) -> str:
    digest = hashlib.sha256(question.strip().lower().encode()).hexdigest()[:16]
    return f"agentans:{user_id}:{digest}"


@app.post("/agent/ask")
async def agent_ask(req: AskRequest):
    """Run the Copilot agent on an English question (ReAct loop over the live tools).

    Caching: stateless questions (no thread_id) reuse a recent identical answer.
    Conversation: with thread_id, prior turns load from Redis and the new turn is saved.
    Degradation: if every model in the fallback chain fails (free-tier exhausted), return a
    clean "at capacity" message instead of a raw error.
    """
    cache_key = _answer_cache_key(DEMO_USER, req.question) if not req.thread_id else None
    if cache_key:
        cached = await rds.get(cache_key)
        if cached is not None:
            return {**json.loads(cached), "cached": True}

    history = (
        await conversation.load_history(rds, DEMO_USER, req.thread_id) if req.thread_id else []
    )
    try:
        result = await copilot.run(
            req.question, deps=Deps(pool=pool), message_history=history, usage_limits=USAGE_LIMITS,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "answer_type": "Error",
                "answer": {"summary": "The assistant is temporarily at capacity (free-tier "
                                      "limit). Please try again in a moment."},
                "tools_used": [],
                "error": type(exc).__name__,
            },
        )

    tools_used = [
        part.tool_name
        for msg in result.all_messages()
        for part in getattr(msg, "parts", [])
        # only tool *calls*, excluding Pydantic AI's internal "final_result_*" output tool
        if isinstance(part, ToolCallPart) and not part.tool_name.startswith("final_result")
    ]
    output = result.output
    response = {
        "answer_type": type(output).__name__,
        "answer": output.model_dump() if hasattr(output, "model_dump") else output,
        "tools_used": tools_used,
    }
    if req.thread_id:
        answer_text = getattr(output, "summary", None) or str(output)
        await conversation.save_turn(rds, DEMO_USER, req.thread_id, req.question, answer_text)
    elif cache_key and "remember" not in tools_used:   # don't cache memory-writes
        await rds.set(cache_key, json.dumps(response, default=str), ex=AGENT_CACHE_TTL)
    return response


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/agent/stream")
async def agent_stream(q: str):
    """Stream the agent's tool steps (live) then the final structured answer, over SSE."""
    async def gen():
        async with copilot.iter(q, deps=Deps(pool=pool), usage_limits=USAGE_LIMITS) as run:
            async for node in run:
                model_response = getattr(node, "model_response", None)
                if model_response is None:
                    continue
                for part in getattr(model_response, "parts", []):
                    name = getattr(part, "tool_name", None)
                    if name and not name.startswith("final_result"):
                        yield _sse("tool", {"tool": name})
            out = run.result.output
            yield _sse("result", {"answer_type": type(out).__name__, "answer": out.model_dump()})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/agent/ag-ui")
async def agent_ag_ui(request: Request):
    """AG-UI protocol endpoint (text output) — what CopilotKit connects to."""
    from pydantic_ai.ui.ag_ui import AGUIAdapter

    return await AGUIAdapter.dispatch_request(
        request,
        agent=copilot,
        deps=Deps(pool=pool),
        output_type=str,           # natural-language chat (override the structured output)
        usage_limits=USAGE_LIMITS,
    )


@app.get("/incidents")
async def list_incidents(limit: int = 20):
    """Recent Watchdog incident reports (newest first)."""
    rows = await fetch(
        "SELECT id, kind, route_id, severity, summary, created_at "
        "FROM incidents ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )
    return {"incidents": rows}


@app.post("/watchdog/run")
async def watchdog_run():
    """Manually trigger one Watchdog pass (detect anomalies, investigate, log incidents)."""
    created = await watchdog.run_once(pool)
    return {"created": created}


async def cached_json(key: str, ttl: int, compute):
    """Return cached JSON for `key`, or run `compute()`, cache it (EX=ttl), return it."""
    hit = await rds.get(key)
    if hit is not None:
        return json.loads(hit)
    data = await compute()
    await rds.set(key, json.dumps(data, default=str), ex=ttl)
    return data


async def fetch(sql: str, params) -> list[dict]:
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        return await cur.fetchall()


@app.get("/health")
async def health():
    """Liveness check: confirms the API and DB are reachable."""
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("SELECT 1")
        await cur.fetchone()
    return {"status": "ok"}


@app.websocket("/ws/vehicles")
async def ws_vehicles(ws: WebSocket):
    """Live vehicle feed: the server pushes position snapshots; clients just listen."""
    await ws.accept()
    clients.add(ws)
    metrics.WS_CLIENTS.set(len(clients))
    try:
        while True:
            await ws.receive_text()  # we don't expect client messages; this detects disconnect
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)
        metrics.WS_CLIENTS.set(len(clients))


@app.get("/vehicles")
async def vehicles(route: str | None = None, limit: int = 2000):
    """Latest known position for each vehicle (optionally filtered by route)."""
    where = "WHERE route_id = %s" if route else ""
    params = ([route] if route else []) + [limit]
    sql = f"""
        SELECT DISTINCT ON (vehicle_id)
            vehicle_id, route_id, trip_id, latitude, longitude, bearing, recorded_at
        FROM vehicle_positions
        {where}
        ORDER BY vehicle_id, recorded_at DESC
        LIMIT %s
    """
    rows = await fetch(sql, params)
    return {"count": len(rows), "vehicles": rows}


@app.get("/vehicles/near")
async def vehicles_near(
    lat: float = Query(...), lon: float = Query(...), radius_m: float = 500
):
    """Vehicles currently within `radius_m` of (lat, lon). Cached for 5s."""
    # Convert metres to degrees so the GEOMETRY GiST index is used. Approximate
    # (longitude degrees shrink with latitude) but fine for a "near me" feature.
    radius_deg = radius_m / 111_320.0
    sql = f"""
        SELECT DISTINCT ON (vehicle_id)
            vehicle_id, route_id, latitude, longitude, bearing, recorded_at
        FROM vehicle_positions
        WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
          AND recorded_at >= now() - interval '{RECENT_WINDOW}'
        ORDER BY vehicle_id, recorded_at DESC
    """

    async def compute():
        rows = await fetch(sql, (lon, lat, radius_deg))
        return {"count": len(rows), "vehicles": rows}

    key = f"near:{round(lat, 4)}:{round(lon, 4)}:{int(radius_m)}"
    return await cached_json(key, ttl=5, compute=compute)


@app.get("/stops/{stop_id}/arrivals")
async def stop_arrivals(stop_id: str):
    """Predicted upcoming arrivals at a stop, for trips currently running today."""
    sql = """
        WITH active AS (
            SELECT trip_id, route_id,
                   max(stop_sequence) AS cur_seq,
                   (array_agg(delay_seconds ORDER BY stop_sequence DESC))[1] AS current_delay
            FROM vehicle_arrivals
            WHERE service_date = (now() AT TIME ZONE 'America/New_York')::date
            GROUP BY trip_id, route_id
            HAVING max(arrived_at) >= now() - interval '30 minutes'  -- still running
        ),
        cand AS (
            SELECT a.trip_id, a.route_id, a.current_delay, st.stop_sequence,
                   (((now() AT TIME ZONE 'America/New_York')::date::timestamp
                     AT TIME ZONE 'America/New_York') + st.arrival_time::interval) AS scheduled_ts
            FROM active a
            JOIN stop_times st
              ON st.trip_id = a.trip_id AND st.stop_id = %s AND st.arrival_time <> ''
            WHERE st.stop_sequence > a.cur_seq        -- trip hasn't reached this stop yet
              AND abs(a.current_delay) <= 1800        -- ignore corrupt (after-midnight) delays
        )
        SELECT trip_id, route_id, current_delay, stop_sequence, scheduled_ts,
               EXTRACT(hour FROM scheduled_ts AT TIME ZONE 'America/New_York')::int AS hour,
               EXTRACT(dow  FROM scheduled_ts AT TIME ZONE 'America/New_York')::int AS dow
        FROM cand
        WHERE scheduled_ts >= now() - interval '2 minutes'           -- future arrivals only
        ORDER BY scheduled_ts
        LIMIT 10
    """
    rows = await fetch(sql, (stop_id,))
    for r in rows:
        r["current_delay"] = float(r["current_delay"] or 0)
    preds = predictor.predict_delays(rows) if predictor.is_loaded() else [None] * len(rows)

    arrivals = []
    for r, d in zip(rows, preds):
        arrivals.append({
            "route_id": r["route_id"],
            "scheduled": r["scheduled_ts"],
            "current_delay_s": round(r["current_delay"]),
            "predicted_delay_s": round(d) if d is not None else None,
            "predicted_eta": r["scheduled_ts"] + timedelta(seconds=d) if d is not None else None,
        })
    m = predictor.meta()
    return {
        "stop_id": stop_id,
        "arrivals": arrivals,
        "accuracy": {
            "mae_model_s": m.get("mae_model_s"),
            "mae_schedule_s": m.get("mae_schedule_s"),
            "mae_persistence_s": m.get("mae_persistence_s"),
        },
    }


@app.get("/vehicles/cell/{h3}")
async def vehicles_in_cell(h3: str):
    """Vehicles currently in the given H3 neighborhood cell."""
    sql = f"""
        SELECT DISTINCT ON (vehicle_id)
            vehicle_id, route_id, latitude, longitude, bearing, recorded_at
        FROM vehicle_positions
        WHERE h3_cell = %s
          AND recorded_at >= now() - interval '{RECENT_WINDOW}'
        ORDER BY vehicle_id, recorded_at DESC
    """
    rows = await fetch(sql, (h3,))
    return {"count": len(rows), "cell": h3, "vehicles": rows}


if __name__ == "__main__":
    import uvicorn

    if sys.platform == "win32":
        # psycopg async requires a SelectorEventLoop. uvicorn would otherwise install
        # a ProactorEventLoop on Windows, so we build the loop ourselves and tell
        # uvicorn not to touch it (loop="none"). On Linux/Docker we just run uvicorn.
        import selectors

        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        asyncio.set_event_loop(loop)
        server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000, loop="none"))
        loop.run_until_complete(server.serve())
    else:
        uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000)

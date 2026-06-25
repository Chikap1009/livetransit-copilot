"""FastAPI app: REST endpoints over the live transit data."""
import asyncio
import json
import sys
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.core import config

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
    task = asyncio.create_task(broadcaster())
    yield
    task.cancel()
    await rds.aclose()
    await pool.close()


app = FastAPI(title="LiveTransit API", lifespan=lifespan)

# Serve the minimal live-map page at /web (same origin as the API -> no CORS for the WS).
app.mount("/web", StaticFiles(directory="frontend", html=True), name="web")


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
    try:
        while True:
            await ws.receive_text()  # we don't expect client messages; this detects disconnect
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)


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

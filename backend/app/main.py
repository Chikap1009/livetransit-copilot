"""FastAPI app: REST endpoints over the live transit data."""
import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.core import config

pool: AsyncConnectionPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the DB connection pool at startup, close it at shutdown."""
    global pool
    pool = AsyncConnectionPool(config.DATABASE_URL, min_size=1, max_size=5, open=False)
    await pool.open()
    yield
    await pool.close()


app = FastAPI(title="LiveTransit API", lifespan=lifespan)


@app.get("/health")
async def health():
    """Liveness check: confirms the API and DB are reachable."""
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("SELECT 1")
        await cur.fetchone()
    return {"status": "ok"}


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
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return {"count": len(rows), "vehicles": rows}


if __name__ == "__main__":
    import uvicorn

    if sys.platform == "win32":
        # psycopg async requires a SelectorEventLoop. uvicorn would otherwise install
        # a ProactorEventLoop on Windows, so we build the loop ourselves and tell
        # uvicorn not to touch it (loop="none"). No-op concern on Linux/Docker, where
        # we just run `uvicorn backend.app.main:app` normally.
        import selectors

        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        asyncio.set_event_loop(loop)
        server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000, loop="none"))
        loop.run_until_complete(server.serve())
    else:
        uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000)

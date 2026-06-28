"""MCP server exposing LiveTransit's read-only tools (Phase I).

Any MCP host (Claude Desktop, Cursor, ...) can connect and call these to drive the live
MBTA transit system. The HOST provides the LLM; this server is pure data tools, so it
uses NO LLM quota. Tools reuse the exact same functions as the in-app agent — one source
of truth, and they're already read-only (the guardrail).

Run for Claude Desktop (stdio):      python -m backend.app.mcp.server
Run networked (Streamable HTTP):     python -m backend.app.mcp.server http
"""
import sys

from mcp.server.fastmcp import FastMCP
from psycopg_pool import AsyncConnectionPool

from backend.app.agent import tools
from backend.app.core import config

mcp = FastMCP(
    "livetransit",
    instructions=(
        "Live MBTA (Boston) transit tools: vehicle positions, arrival predictions, "
        "service alerts, trip planning, policy/alert search, and weather."
    ),
)

_pool: AsyncConnectionPool | None = None


async def _pool_() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(config.DATABASE_URL, min_size=1, max_size=3, open=False)
        await _pool.open()
    return _pool


@mcp.tool()
async def get_vehicle_positions(route: str) -> dict:
    """Current positions of vehicles running an MBTA route (e.g. 'Red', 'Orange', '66')."""
    return await tools.get_vehicle_positions(await _pool_(), route)


@mcp.tool()
async def predict_eta(stop_id: str) -> dict:
    """Predicted upcoming arrivals (with delays) at an MBTA stop id (e.g. '70061')."""
    return await tools.predict_eta(await _pool_(), stop_id)


@mcp.tool()
async def get_service_alerts(route: str | None = None) -> dict:
    """Current MBTA service alerts, optionally filtered to a single route id."""
    return await tools.get_service_alerts(route)


@mcp.tool()
async def plan_trip(origin: str, destination: str) -> dict:
    """Plan a trip between two stops by name (a direct ride, or rail transfers)."""
    return await tools.plan_trip(await _pool_(), origin, destination)


@mcp.tool()
async def search_docs(query: str) -> dict:
    """Search MBTA service alerts + agency policy/reference docs for relevant passages."""
    return await tools.search_docs(await _pool_(), query)


@mcp.tool()
async def get_weather() -> dict:
    """Current Boston weather, useful for reasoning about delays."""
    return await tools.get_weather()


if __name__ == "__main__":
    # psycopg's async pool needs a SelectorEventLoop on Windows (Proactor is the default).
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    http = len(sys.argv) > 1 and sys.argv[1] in ("http", "streamable-http")
    mcp.run(transport="streamable-http" if http else "stdio")

"""The Copilot: a Pydantic AI ReAct agent with read-only tools over the live data."""
from dataclasses import dataclass

from psycopg_pool import AsyncConnectionPool
from pydantic_ai import Agent, RunContext

from backend.app.agent import tools
from backend.app.agent.gateway import MODEL
from backend.app.agent.schemas import Answer, ArrivalAnswer


@dataclass
class Deps:
    """Dependencies handed to tools at run time (here: the DB pool)."""
    pool: AsyncConnectionPool


SYSTEM_PROMPT = (
    "You are LiveTransit Copilot, an assistant for the MBTA (Boston) transit system. "
    "You have tools that read LIVE data. ALWAYS call a tool to answer questions about "
    "current vehicle positions, predicted arrivals, or service alerts — never guess from "
    "memory. Routes are named like 'Red', 'Orange', 'Blue', 'Green-B', or bus numbers like "
    "'1' or '66'. Be concise and specific; if a tool returns no data, say so plainly."
)

copilot = Agent(
    MODEL,
    deps_type=Deps,
    output_type=[ArrivalAnswer, Answer],   # the model fills (and we validate) one of these
    system_prompt=SYSTEM_PROMPT,
)


@copilot.tool
async def get_vehicle_positions(ctx: RunContext[Deps], route: str) -> dict:
    """Get the current positions of vehicles running on an MBTA route.

    route: the MBTA route id, e.g. 'Red', 'Orange', 'Green-B', '1', '66'.
    """
    return await tools.get_vehicle_positions(ctx.deps.pool, route)


@copilot.tool
async def predict_eta(ctx: RunContext[Deps], stop_id: str) -> dict:
    """Predict upcoming arrivals (with delays in seconds) at an MBTA stop.

    stop_id: the MBTA stop id (e.g. '70061').
    """
    return await tools.predict_eta(ctx.deps.pool, stop_id)


@copilot.tool
async def get_service_alerts(ctx: RunContext[Deps], route: str | None = None) -> dict:
    """Get current MBTA service alerts. Optionally filter to a single route id."""
    return await tools.get_service_alerts(route)

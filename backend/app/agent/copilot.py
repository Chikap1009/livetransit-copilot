"""The Copilot: a Pydantic AI ReAct agent with read-only tools over the live data."""
from dataclasses import dataclass

from psycopg_pool import AsyncConnectionPool
from pydantic_ai import Agent, RunContext

from backend.app.agent import memory, tools
from backend.app.agent.gateway import MODEL
from backend.app.agent.schemas import Answer, ArrivalAnswer


@dataclass
class Deps:
    """Dependencies handed to tools at run time (the DB pool + who's asking)."""
    pool: AsyncConnectionPool
    user_id: str = "demo"


SYSTEM_PROMPT = (
    "You are LiveTransit Copilot, an assistant for the MBTA (Boston) transit system. "
    "You have tools that read LIVE data.\n"
    "CRITICAL WORKFLOW: for ANY question about current vehicle positions, predicted arrivals, "
    "or service alerts, you MUST FIRST call the relevant tool and WAIT for its result, and only "
    "THEN write your final answer using that result. Never write a final answer that says you "
    "'will check' or describes intent — actually call the tool first. Never invent data from "
    "memory.\n"
    "Routes are named like 'Red', 'Orange', 'Blue', 'Green-B', or bus numbers like '1' or '66'.\n"
    "You can also DRAW ON THE MAP with these actions: highlightRoute(route) to highlight a route "
    "line, dropPin(lat, lon, label) to mark a location, drawTrip(legs) to draw a planned trip, and "
    "clearMap to reset. When the user asks to SHOW, HIGHLIGHT, or POINT OUT a route on the map, "
    "call highlightRoute (and still give a short text reply).\n"
    "TRIP PLANNING: when the user asks how to get from one place to another (A to B), call "
    "plan_trip(origin, destination). It returns a journey that may be a single direct ride or "
    "several legs with transfers. Then call drawTrip and pass it plan_trip's `draw` array as the "
    "`legs` argument to draw the whole trip on the map. In your text reply, walk through each leg "
    "(which line, board where, get off where, the per-leg minutes) and state the total journey "
    "time using the tool's `total_minutes` value verbatim (it already includes waiting at "
    "transfers) — do not recompute it. If a trip has transfers, clearly say where to change lines. "
    "If plan_trip returns found=false, relay its message.\n"
    "MEMORY: when the user tells you a durable fact about themselves — their home or work "
    "stop, or a travel preference (e.g. 'my home stop is Davis', 'I prefer fewer transfers') — "
    "call remember(fact, kind) to save it (kind is 'place' for stops, 'preference' for "
    "preferences, else 'fact'). Always phrase the saved fact as a complete, self-describing "
    "statement — 'home stop is Davis', 'work stop is Kendall', 'prefers fewer transfers' — never "
    "just a bare value like 'Davis'. Known facts about the user are given to you below and you "
    "should use them without being asked (e.g. 'how do I get home?' uses their home stop). For "
    "anything else you might have been told before, call recall(query).\n"
    "Be concise and specific; if a tool returns no data, say so plainly."
)

copilot = Agent(
    MODEL,
    deps_type=Deps,
    output_type=[ArrivalAnswer, Answer],   # the model fills (and we validate) one of these
    system_prompt=SYSTEM_PROMPT,
)


@copilot.system_prompt
async def _inject_user_memory(ctx: RunContext[Deps]) -> str:
    """Append the user's saved preferences/places so the agent uses them unprompted."""
    prefs = await memory.load_preferences(ctx.deps.pool, ctx.deps.user_id)
    if not prefs:
        return ""
    lines = "\n".join(f"- ({p['kind']}) {p['content']}" for p in prefs)
    return f"Known facts about this user:\n{lines}"


@copilot.tool
async def remember(ctx: RunContext[Deps], fact: str, kind: str = "fact") -> dict:
    """Save a durable fact about the user. kind: 'place' | 'preference' | 'fact'.

    Use for home/work stops and travel preferences the user states. Phrase `fact` as a
    complete statement, e.g. 'home stop is Davis' — not a bare value like 'Davis'.
    """
    await memory.remember(ctx.deps.pool, ctx.deps.user_id, kind, fact)
    return {"saved": fact, "kind": kind}


@copilot.tool
async def recall(ctx: RunContext[Deps], query: str, k: int = 5) -> dict:
    """Recall durable facts previously saved about the user, by similarity to a query."""
    rows = await memory.recall(ctx.deps.pool, ctx.deps.user_id, query, k)
    return {"memories": [r["content"] for r in rows]}


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
async def plan_trip(ctx: RunContext[Deps], origin: str, destination: str) -> dict:
    """Plan a trip between two places by stop/station name.

    Returns a journey with one or more legs. A direct ride has one leg; otherwise
    it routes over the subway/rail network with transfers. Each leg has the route,
    where to board and alight, scheduled times and minutes. The `draw` array is
    pre-shaped to pass straight to the drawTrip map action.

    origin/destination: stop or station names, e.g. 'Kendall', 'Park Street', 'Airport'.
    """
    return await tools.plan_trip(ctx.deps.pool, origin, destination)


@copilot.tool
async def get_service_alerts(ctx: RunContext[Deps], route: str | None = None) -> dict:
    """Get current MBTA service alerts. Optionally filter to a single route id."""
    return await tools.get_service_alerts(route)

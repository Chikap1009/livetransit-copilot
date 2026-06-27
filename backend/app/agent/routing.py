"""Lightweight GTFS trip planning for the Copilot (Phase C finale).

Two modes:
  * DIRECT  — a single trip on any route (incl. buses) gets you A -> B.
  * TRANSFER — no direct trip, so we route over the rapid-transit network
               (subway / light-rail / commuter-rail, route_type 0,1,2) with a
               minimum-transfers breadth-first search, then fill in scheduled
               times leg by leg.

The BFS chooses *which lines and where to change*; a scheduled-times query
fills in *the clock* for each leg (next departure, arrival, duration), chained
so each leg departs after the previous one arrives (+ a transfer buffer).

This is intentionally not a full time-dependent router (that's OpenTripPlanner,
a heavy stretch goal). It answers the common "how do I get from A to B, and how
long?" with honest scheduled times and the transfers spelled out.
"""
from collections import deque
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

NY = ZoneInfo("America/New_York")
RAIL_TYPES = (0, 1, 2)          # tram/light-rail, subway, commuter/heavy rail
MAX_LEGS = 4                    # give up beyond 3 transfers
TRANSFER_BUFFER = timedelta(minutes=3)   # wait/walk allowance at a transfer
MAX_PLATFORMS = 60             # cap the name-match fan-out

# GTFS arrival/departure are local "HH:MM:SS" strings that can exceed 24h
# (e.g. 25:10:00 = 1:10am next day). Turn one into an absolute timestamptz on
# today's New-York service date by adding it as an interval to local midnight.
def _abs_ts(col: str) -> str:
    return (
        "(((now() AT TIME ZONE 'America/New_York')::date::timestamp "
        f"AT TIME ZONE 'America/New_York') + {col}::interval)"
    )


# --- the rapid-transit graph (static; built once and cached per process) ------
_RAIL_GRAPH: dict | None = None


async def _build_rail_graph(pool: AsyncConnectionPool) -> dict:
    """station_routes, route_stations, station_platforms, station_meta for rail."""
    sql = """
        SELECT DISTINCT t.route_id,
               COALESCE(NULLIF(s.parent_station, ''), s.stop_id) AS station,
               s.stop_id, s.stop_name, s.stop_lat, s.stop_lon
        FROM stop_times st
        JOIN trips t  ON t.trip_id = st.trip_id
        JOIN routes r ON r.route_id = t.route_id
        JOIN stops s  ON s.stop_id = st.stop_id
        WHERE r.route_type = ANY(%s)
    """
    station_routes: dict[str, set] = {}
    route_stations: dict[str, set] = {}
    station_platforms: dict[str, set] = {}
    station_meta: dict[str, dict] = {}
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, (list(RAIL_TYPES),))
        rows = await cur.fetchall()
    for r in rows:
        st, rt = r["station"], r["route_id"]
        station_routes.setdefault(st, set()).add(rt)
        route_stations.setdefault(rt, set()).add(st)
        station_platforms.setdefault(st, set()).add(r["stop_id"])
        m = station_meta.setdefault(st, {"name": r["stop_name"], "lats": [], "lons": []})
        m["lats"].append(r["stop_lat"])
        m["lons"].append(r["stop_lon"])
    for st, m in station_meta.items():
        m["lat"] = sum(m["lats"]) / len(m["lats"])
        m["lon"] = sum(m["lons"]) / len(m["lons"])
        del m["lats"], m["lons"]
    return {
        "station_routes": station_routes,
        "route_stations": route_stations,
        "station_platforms": {k: list(v) for k, v in station_platforms.items()},
        "station_meta": station_meta,
    }


async def get_rail_graph(pool: AsyncConnectionPool) -> dict:
    global _RAIL_GRAPH
    if _RAIL_GRAPH is None:
        _RAIL_GRAPH = await _build_rail_graph(pool)
    return _RAIL_GRAPH


# --- stop-name resolution ----------------------------------------------------
async def _resolve_candidates(pool: AsyncConnectionPool, name: str) -> list[dict]:
    """Boarding stops whose name matches, cleanest/exact names ranked first.

    Ordering matters: a query like 'Harvard' matches the clean subway station
    *and* many bus stops ('Western Ave @ N Harvard St'). We surface exact then
    prefix matches first so the LIMIT can't drop the real station.
    """
    sql = """
        SELECT s.stop_id,
               COALESCE(NULLIF(s.parent_station, ''), s.stop_id) AS station,
               s.stop_name, s.stop_lat, s.stop_lon
        FROM stops s
        WHERE s.stop_name ILIKE %(pat)s
          AND EXISTS (SELECT 1 FROM stop_times st WHERE st.stop_id = s.stop_id)
        ORDER BY (lower(s.stop_name) = lower(%(q)s)) DESC,
                 (s.stop_name ILIKE %(pfx)s) DESC,
                 length(s.stop_name)
        LIMIT %(lim)s
    """
    params = {"q": name, "pfx": f"{name}%", "pat": f"%{name}%", "lim": MAX_PLATFORMS}
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        return await cur.fetchall()


def _name_score(stop_name: str, query: str) -> int:
    nm, q = stop_name.lower(), query.strip().lower()
    if nm == q:
        return 0
    if nm.startswith(q):
        return 1
    return 2


async def _resolve_station(pool: AsyncConnectionPool, graph: dict, name: str) -> dict | None:
    """Pick the single best station for a name: rail-preferred, exact/prefix-preferred.

    Returns its platform stop_ids (all of them, for a rail station) plus a
    representative display name and coordinates, or None if nothing matches.
    """
    cands = await _resolve_candidates(pool, name)
    if not cands:
        return None
    groups: dict[str, list] = {}
    for c in cands:
        groups.setdefault(c["station"], []).append(c)
    scored = []
    for station, rows in groups.items():
        is_rail = station in graph["station_routes"]
        best_ns = min(_name_score(r["stop_name"], name) for r in rows)
        rep = min((r["stop_name"] for r in rows), key=len)
        # lower is better: rail first, then exact/prefix, then shorter name
        scored.append(((0 if is_rail else 1, best_ns, len(rep)), station, rows))
    scored.sort(key=lambda x: x[0])
    _, station, rows = scored[0]
    if station in graph["station_routes"]:
        meta = graph["station_meta"][station]
        return {
            "station": station, "name": meta["name"], "is_rail": True,
            "platforms": graph["station_platforms"][station],
            "lat": meta["lat"], "lon": meta["lon"],
        }
    return {
        "station": station, "name": min((r["stop_name"] for r in rows), key=len),
        "is_rail": False, "platforms": [r["stop_id"] for r in rows],
        "lat": sum(r["stop_lat"] for r in rows) / len(rows),
        "lon": sum(r["stop_lon"] for r in rows) / len(rows),
    }


# --- a single timed leg ------------------------------------------------------
async def _find_leg(
    pool: AsyncConnectionPool,
    board_ids: list[str],
    alight_ids: list[str],
    ready_ts: datetime,
    route: str | None = None,
) -> dict | None:
    """Soonest single trip boarding in board_ids then alighting in alight_ids."""
    route_clause = "AND t.route_id = %(route)s" if route else ""
    sql = f"""
        SELECT t.route_id,
               sb.stop_id  AS board_id,  sb.stop_name AS board_name,
               sb.stop_lat AS board_lat, sb.stop_lon  AS board_lon,
               sa.stop_id  AS alight_id, sa.stop_name AS alight_name,
               sa.stop_lat AS alight_lat, sa.stop_lon AS alight_lon,
               {_abs_ts('s1.departure_time')} AS depart_ts,
               {_abs_ts('s2.arrival_time')}   AS arrive_ts
        FROM stop_times s1
        JOIN stop_times s2 ON s2.trip_id = s1.trip_id AND s2.stop_sequence > s1.stop_sequence
        JOIN trips t  ON t.trip_id = s1.trip_id
        JOIN stops sb ON sb.stop_id = s1.stop_id
        JOIN stops sa ON sa.stop_id = s2.stop_id
        WHERE s1.stop_id = ANY(%(board)s) AND s2.stop_id = ANY(%(alight)s)
          AND s1.departure_time <> '' AND s2.arrival_time <> ''
          {route_clause}
          AND {_abs_ts('s1.departure_time')} >= %(ready)s
        ORDER BY depart_ts
        LIMIT 1
    """
    params = {"board": board_ids, "alight": alight_ids, "ready": ready_ts}
    if route:
        params["route"] = route
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        return await cur.fetchone()


# --- minimum-transfers BFS over the rail graph -------------------------------
def _bfs(graph: dict, origins: set[str], dests: set[str]) -> list[tuple] | None:
    """Fewest-legs path. Returns [(route, board_station, alight_station), ...]."""
    station_routes = graph["station_routes"]
    route_stations = graph["route_stations"]
    origins = {s for s in origins if s in station_routes}
    dests = {s for s in dests if s in station_routes}
    if not origins or not dests:
        return None
    if origins & dests:                       # same station -> no trip needed
        return []
    visited = set(origins)
    came: dict[str, tuple] = {}               # station -> (prev_station, route)
    queue = deque((s, 0) for s in origins)
    while queue:
        station, depth = queue.popleft()
        if depth >= MAX_LEGS:
            continue
        for route in station_routes.get(station, ()):
            for nxt in route_stations.get(route, ()):
                if nxt in visited:
                    continue
                came[nxt] = (station, route)
                if nxt in dests:
                    return _reconstruct(came, nxt)
                visited.add(nxt)
                queue.append((nxt, depth + 1))
    return None


def _reconstruct(came: dict, end: str) -> list[tuple]:
    legs = []
    cur = end
    while cur in came:
        prev, route = came[cur]
        legs.append((route, prev, cur))
        cur = prev
    legs.reverse()
    return legs


# --- orchestration -----------------------------------------------------------
def _clock(dt: datetime | None) -> str | None:
    if not dt:
        return None
    # %-I (no zero-pad) is Linux-only; do it portably for Windows dev too.
    return dt.astimezone(NY).strftime("%I:%M %p").lstrip("0")


def _leg_payload(route, board_name, board_lat, board_lon,
                 alight_name, alight_lat, alight_lon, depart, arrive):
    minutes = round((arrive - depart).total_seconds() / 60) if depart and arrive else None
    return {
        "route": route,
        "board": board_name, "board_lat": board_lat, "board_lon": board_lon,
        "alight": alight_name, "alight_lat": alight_lat, "alight_lon": alight_lon,
        "departs": _clock(depart), "arrives": _clock(arrive), "minutes": minutes,
        # pre-shaped for the frontend drawTrip(legs) action:
        "draw": {
            "route": route,
            "fromLat": board_lat, "fromLon": board_lon, "fromLabel": board_name,
            "toLat": alight_lat, "toLon": alight_lon, "toLabel": alight_name,
        },
    }


async def plan_trip(pool: AsyncConnectionPool, origin: str, destination: str) -> dict:
    """Plan a direct-or-transfer trip from origin to destination (by stop name)."""
    graph = await get_rail_graph(pool)
    o = await _resolve_station(pool, graph, origin)
    d = await _resolve_station(pool, graph, destination)
    if not o:
        return {"found": False, "message": f"I couldn't find a stop matching '{origin}'."}
    if not d:
        return {"found": False, "message": f"I couldn't find a stop matching '{destination}'."}

    o_name, d_name = o["name"], d["name"]
    now = datetime.now(timezone.utc)

    # 1) Try a single direct trip on any route (subway or bus).
    direct = await _find_leg(pool, o["platforms"], d["platforms"], now)
    if direct:
        leg = _leg_payload(
            direct["route_id"], direct["board_name"], direct["board_lat"], direct["board_lon"],
            direct["alight_name"], direct["alight_lat"], direct["alight_lon"],
            direct["depart_ts"], direct["arrive_ts"],
        )
        return {
            "found": True, "origin": o_name, "destination": d_name, "transfers": 0,
            "total_minutes": leg["minutes"],
            "departs": leg["departs"], "arrives": leg["arrives"],
            "legs": [leg], "draw": [leg["draw"]],
        }

    # 2) No direct trip -> minimum-transfers BFS over the rail network.
    path = _bfs(graph, {o["station"]}, {d["station"]})
    if not path:
        return {
            "found": False, "origin": o_name, "destination": d_name,
            "message": (
                f"I couldn't find a direct route from {o_name} to {d_name}, and at least one "
                "of them isn't on the subway/rail network — I can plan direct routes (any line) "
                "and rail transfers, but not multi-bus trips."
            ),
        }

    # 3) Fill in scheduled times leg by leg, chaining departures.
    meta = graph["station_meta"]
    platforms = graph["station_platforms"]
    legs, ready = [], now
    first_depart: datetime | None = None
    last_arrive: datetime | None = None
    for route, bstation, astation in path:
        leg_row = await _find_leg(
            pool, platforms[bstation], platforms[astation], ready, route=route,
        )
        if not leg_row:
            legs.append(_leg_payload(
                route, meta[bstation]["name"], meta[bstation]["lat"], meta[bstation]["lon"],
                meta[astation]["name"], meta[astation]["lat"], meta[astation]["lon"], None, None,
            ))
            continue
        legs.append(_leg_payload(
            leg_row["route_id"], leg_row["board_name"], leg_row["board_lat"], leg_row["board_lon"],
            leg_row["alight_name"], leg_row["alight_lat"], leg_row["alight_lon"],
            leg_row["depart_ts"], leg_row["arrive_ts"],
        ))
        if first_depart is None:
            first_depart = leg_row["depart_ts"]
        last_arrive = leg_row["arrive_ts"]
        ready = leg_row["arrive_ts"] + TRANSFER_BUFFER

    # Total = wall-clock from the first boarding to the last arrival (incl. waits),
    # only when every leg was timed.
    total = None
    if first_depart and last_arrive and all(leg["minutes"] is not None for leg in legs):
        total = round((last_arrive - first_depart).total_seconds() / 60)
    return {
        "found": True, "origin": o_name, "destination": d_name,
        "transfers": len(legs) - 1,
        "total_minutes": total,
        "departs": legs[0]["departs"], "arrives": legs[-1]["arrives"],
        "legs": legs, "draw": [leg["draw"] for leg in legs],
    }

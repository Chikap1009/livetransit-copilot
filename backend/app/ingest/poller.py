"""Poller: fetch MBTA VehiclePositions every ~N seconds, decode, store.

Standalone long-lived process, separate from the API (background work vs.
request handling). Run:
    .venv\\Scripts\\python.exe -m backend.app.ingest.poller            # forever
    .venv\\Scripts\\python.exe -m backend.app.ingest.poller --ticks 2  # test: 2 polls then exit
"""
import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone

import httpx
import psycopg
from google.transit import gtfs_realtime_pb2

from backend.app.core import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("poller")

# geom is built in SQL from (lon, lat) — note lon first.
INSERT_SQL = """
    INSERT INTO vehicle_positions
        (vehicle_id, trip_id, route_id, latitude, longitude, geom, bearing, recorded_at)
    VALUES
        (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
"""


def parse_feed(raw: bytes) -> list[tuple]:
    """Decode protobuf bytes into rows ready for INSERT_SQL."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(raw)
    rows = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        pos = v.position
        recorded_at = (
            datetime.fromtimestamp(v.timestamp, tz=timezone.utc) if v.timestamp else None
        )
        bearing = pos.bearing if pos.HasField("bearing") else None
        rows.append((
            v.vehicle.id or None,         # vehicle_id
            v.trip.trip_id or None,       # trip_id
            v.trip.route_id or None,      # route_id
            pos.latitude,                 # latitude
            pos.longitude,                # longitude
            pos.longitude,                # \ geom: ST_MakePoint(lon, lat)
            pos.latitude,                 # /
            bearing,                      # bearing
            recorded_at,                  # recorded_at (UTC)
        ))
    return rows


async def poll_once(client: httpx.AsyncClient, conn: psycopg.AsyncConnection) -> int:
    """One fetch -> decode -> store cycle. Returns rows stored."""
    resp = await client.get(config.MBTA_VEHICLE_POSITIONS_URL, timeout=15)
    resp.raise_for_status()
    rows = parse_feed(resp.content)
    async with conn.cursor() as cur:
        await cur.executemany(INSERT_SQL, rows)
    await conn.commit()
    return len(rows)


async def main(max_ticks: int = 0) -> None:
    log.info("poller starting; interval=%ss", config.POLL_INTERVAL_SECONDS)
    async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
        async with httpx.AsyncClient() as client:
            tick = 0
            while True:
                start = time.monotonic()
                try:
                    n = await poll_once(client, conn)
                    log.info("stored %d vehicle positions", n)
                except Exception as exc:              # survive any failure
                    log.warning("poll failed: %s", exc)
                    await conn.rollback()
                tick += 1
                if max_ticks and tick >= max_ticks:
                    break
                elapsed = time.monotonic() - start
                await asyncio.sleep(max(0.0, config.POLL_INTERVAL_SECONDS - elapsed))


def run(coro):
    """Run an async entrypoint, working around a Windows-only asyncio quirk.

    psycopg's async mode requires a SelectorEventLoop; Windows defaults to a
    ProactorEventLoop. On Linux (e.g. inside Docker) the default already works,
    so this branch is a no-op there.
    """
    if sys.platform == "win32":
        return asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop)
    return asyncio.run(coro)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=0, help="stop after N polls (0=forever)")
    run(main(max_ticks=parser.parse_args().ticks))

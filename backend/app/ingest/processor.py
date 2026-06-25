"""Processor: consume `vehicles:stream` and write positions to PostGIS.

Phase 2: reads the Redis Stream via a consumer group (at-least-once delivery),
inserts idempotently (ON CONFLICT DO NOTHING on the dedupe key), then XACKs.
Run:
    .venv\\Scripts\\python.exe -m backend.app.ingest.processor            # forever
    .venv\\Scripts\\python.exe -m backend.app.ingest.processor --ticks 3  # test: 3 batches then exit
"""
import argparse
import logging
from datetime import datetime, timezone

import h3
import psycopg
import redis.asyncio as redis
from redis.exceptions import ResponseError

from backend.app.core import config
from backend.app.core.asyncrun import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("processor")

STREAM = "vehicles:stream"
GROUP = "writers"
CONSUMER = "c1"
BATCH = 500

INSERT_SQL = """
    INSERT INTO vehicle_positions
        (vehicle_id, trip_id, route_id, latitude, longitude, geom, bearing, recorded_at, h3_cell)
    VALUES
        (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
    ON CONFLICT (vehicle_id, recorded_at) DO NOTHING
"""


def to_row(f: dict) -> tuple:
    """Convert a stream message's fields into INSERT_SQL params."""
    ts = datetime.fromtimestamp(int(f["ts"]), tz=timezone.utc) if f.get("ts") else None
    lon, lat = float(f["lon"]), float(f["lat"])
    bearing = float(f["bearing"]) if f.get("bearing") else None
    h3_cell = h3.latlng_to_cell(lat, lon, config.H3_RESOLUTION)
    return (
        f["vehicle_id"] or None, f["trip_id"] or None, f["route_id"] or None,
        lat, lon, lon, lat, bearing, ts, h3_cell,
    )


async def ensure_group(r: redis.Redis) -> None:
    """Create the consumer group (and the stream) if it doesn't exist yet."""
    try:
        await r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        log.info("created consumer group %s on %s", GROUP, STREAM)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):  # already exists -> fine
            raise


async def main(max_ticks: int = 0) -> None:
    log.info("processor starting; group=%s consumer=%s", GROUP, CONSUMER)
    r = redis.from_url(config.REDIS_URL, decode_responses=True)
    await ensure_group(r)
    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            tick = 0
            while True:
                resp = await r.xreadgroup(
                    GROUP, CONSUMER, {STREAM: ">"}, count=BATCH, block=5000
                )
                if not resp:
                    continue  # no new messages within the block window; loop again
                entries = resp[0][1]                       # [(msg_id, {fields}), ...]
                ids = [msg_id for msg_id, _ in entries]
                rows = [to_row(fields) for _, fields in entries]
                async with conn.cursor() as cur:
                    await cur.executemany(INSERT_SQL, rows)
                await conn.commit()
                await r.xack(STREAM, GROUP, *ids)          # only ack after a durable write
                log.info("processed %d messages", len(ids))
                tick += 1
                if max_ticks and tick >= max_ticks:
                    break
    finally:
        await r.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=0, help="stop after N batches (0=forever)")
    run(main(max_ticks=parser.parse_args().ticks))

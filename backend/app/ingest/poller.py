"""Poller: fetch MBTA VehiclePositions every ~N seconds and PUBLISH to a Redis Stream.

Phase 2: the poller no longer writes the database. It only decodes the feed and
XADDs each vehicle onto the stream `vehicles:stream`. A separate processor consumes
the stream and writes the DB (decoupling + backpressure + resilience). Run:
    .venv\\Scripts\\python.exe -m backend.app.ingest.poller            # forever
    .venv\\Scripts\\python.exe -m backend.app.ingest.poller --ticks 2  # test: 2 polls then exit
"""
import argparse
import asyncio
import logging
import time

import httpx
import redis.asyncio as redis
from google.transit import gtfs_realtime_pb2
from prometheus_client import start_http_server

from backend.app.core import config, metrics
from backend.app.core.asyncrun import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("poller")

STREAM = "vehicles:stream"
STREAM_MAXLEN = 200_000  # cap stream size so it can't grow unbounded


def parse_feed(raw: bytes) -> list[dict]:
    """Decode protobuf bytes into stream-ready field dicts (all values strings)."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(raw)
    out = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        if not v.HasField("position"):
            continue
        pos = v.position
        out.append({
            "vehicle_id": v.vehicle.id or "",
            "trip_id": v.trip.trip_id or "",
            "route_id": v.trip.route_id or "",
            "lat": repr(pos.latitude),
            "lon": repr(pos.longitude),
            "bearing": repr(pos.bearing) if pos.HasField("bearing") else "",
            "ts": str(v.timestamp) if v.timestamp else "",
        })
    return out


async def poll_once(client: httpx.AsyncClient, r: redis.Redis) -> int:
    """One fetch -> decode -> publish cycle. Returns vehicles published."""
    resp = await client.get(config.MBTA_VEHICLE_POSITIONS_URL, timeout=15)
    resp.raise_for_status()
    rows = parse_feed(resp.content)
    ts_values = [int(f["ts"]) for f in rows if f["ts"]]
    if ts_values:
        metrics.FEED_TS.set(max(ts_values))   # newest vehicle timestamp -> feed freshness
    # Pipeline the XADDs into a single round-trip.
    async with r.pipeline(transaction=False) as pipe:
        for fields in rows:
            pipe.xadd(STREAM, fields, maxlen=STREAM_MAXLEN, approximate=True)
        await pipe.execute()
    return len(rows)


async def main(max_ticks: int = 0) -> None:
    log.info("poller starting; interval=%ss stream=%s", config.POLL_INTERVAL_SECONDS, STREAM)
    if not max_ticks:
        start_http_server(metrics.METRICS_PORT_POLLER)  # expose /metrics for Prometheus
    r = redis.from_url(config.REDIS_URL)
    try:
        async with httpx.AsyncClient() as client:
            tick = 0
            while True:
                start = time.monotonic()
                metrics.POLLS.inc()
                try:
                    n = await poll_once(client, r)
                    metrics.POSITIONS_PUBLISHED.inc(n)
                    log.info("published %d vehicle positions", n)
                except Exception as exc:              # survive any failure
                    metrics.POLL_FAILURES.inc()
                    log.warning("poll failed: %s", exc)
                tick += 1
                if max_ticks and tick >= max_ticks:
                    break
                elapsed = time.monotonic() - start
                await asyncio.sleep(max(0.0, config.POLL_INTERVAL_SECONDS - elapsed))
    finally:
        await r.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=0, help="stop after N polls (0=forever)")
    run(main(max_ticks=parser.parse_args().ticks))

"""Unit tests for the ingestion logic that would silently corrupt data if wrong:
protobuf decoding/filtering (poller.parse_feed) and row construction incl. the
(lon, lat) order and recorded_at fallback (processor.to_row).
"""
from datetime import datetime, timezone

import pytest
from google.transit import gtfs_realtime_pb2

from backend.app.ingest.poller import parse_feed
from backend.app.ingest.processor import to_row


def _make_feed() -> bytes:
    """A synthetic VehiclePositions feed: 1 valid vehicle, 1 without position, 1 alert."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"

    e1 = feed.entity.add()
    e1.id = "1"
    v = e1.vehicle
    v.vehicle.id = "y1234"
    v.trip.trip_id = "t-1"
    v.trip.route_id = "Red"
    v.position.latitude = 42.3601
    v.position.longitude = -71.0589
    v.position.bearing = 90.0
    v.timestamp = 1700000000

    e2 = feed.entity.add()                 # vehicle WITHOUT a position -> skipped
    e2.id = "2"
    e2.vehicle.vehicle.id = "noPos"

    e3 = feed.entity.add()                 # not a vehicle (alert) -> skipped
    e3.id = "3"
    e3.alert.header_text.translation.add().text = "delay"

    return feed.SerializeToString()


def test_parse_feed_keeps_only_vehicles_with_position():
    rows = parse_feed(_make_feed())
    assert len(rows) == 1
    r = rows[0]
    assert r["vehicle_id"] == "y1234"
    assert r["route_id"] == "Red"
    # GTFS-RT stores lat/lon as 32-bit floats, so compare approximately.
    assert float(r["lat"]) == pytest.approx(42.3601, abs=1e-4)
    assert float(r["lon"]) == pytest.approx(-71.0589, abs=1e-4)
    assert r["ts"] == "1700000000"


def test_to_row_lonlat_order_and_types():
    f = {"vehicle_id": "v1", "trip_id": "t1", "route_id": "Red",
         "lat": "42.36", "lon": "-71.06", "bearing": "90", "ts": "1700000000"}
    row = to_row(f)
    # (vehicle_id, trip_id, route_id, lat, lon, lon, lat, bearing, ts, h3_cell)
    assert row[0] == "v1"
    assert row[3] == 42.36 and row[4] == -71.06
    assert row[5] == -71.06 and row[6] == 42.36          # geom args = (lon, lat) — the classic trap
    assert row[7] == 90.0
    assert row[8] == datetime.fromtimestamp(1700000000, tz=timezone.utc)
    assert isinstance(row[9], str) and len(row[9]) > 0   # an H3 cell id


def test_to_row_recorded_at_falls_back_to_now_and_empties_become_none():
    f = {"vehicle_id": "v1", "trip_id": "", "route_id": "", "lat": "42.0", "lon": "-71.0",
         "bearing": "", "ts": ""}
    before = datetime.now(timezone.utc)
    row = to_row(f)
    assert row[1] is None                                # empty trip_id -> NULL
    assert row[7] is None                                # missing bearing -> NULL
    assert (row[8] - before).total_seconds() < 5         # recorded_at ~ now (the NOT NULL fallback)

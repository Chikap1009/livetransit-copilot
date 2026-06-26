"""Integration tests against a real (disposable) Postgres: the data-integrity
contracts that matter most — idempotent ingestion and latest-per-vehicle reads.
Exercises the processor's REAL INSERT_SQL.
"""
from backend.app.ingest.processor import INSERT_SQL, to_row


def _fields(vehicle="v1", ts="1700000000"):
    return {"vehicle_id": vehicle, "trip_id": "t1", "route_id": "Red",
            "lat": "42.36", "lon": "-71.06", "bearing": "90", "ts": ts}


def test_insert_is_idempotent(db):
    """Same (vehicle_id, recorded_at) inserted twice -> exactly one row (ON CONFLICT)."""
    row = to_row(_fields())
    with db.cursor() as cur:
        cur.execute(INSERT_SQL, row)
        cur.execute(INSERT_SQL, row)            # duplicate -> ignored
        cur.execute("SELECT count(*) FROM vehicle_positions")
        assert cur.fetchone()[0] == 1


def test_history_kept_and_latest_per_vehicle(db):
    """Different timestamps for one vehicle are BOTH kept (history); the latest wins on read."""
    with db.cursor() as cur:
        cur.execute(INSERT_SQL, to_row(_fields(ts="1700000000")))
        cur.execute(INSERT_SQL, to_row(_fields(ts="1700000600")))   # 10 min later
        cur.execute("SELECT count(*) FROM vehicle_positions")
        assert cur.fetchone()[0] == 2

        cur.execute(
            "SELECT DISTINCT ON (vehicle_id) recorded_at FROM vehicle_positions "
            "ORDER BY vehicle_id, recorded_at DESC"
        )
        assert cur.fetchone()[0].timestamp() == 1700000600


def test_geom_built_with_lon_lat_order(db):
    """geom must be built as (lon, lat) — decode it back and check it's in Boston."""
    with db.cursor() as cur:
        cur.execute(INSERT_SQL, to_row(_fields()))
        cur.execute("SELECT ST_Y(geom), ST_X(geom) FROM vehicle_positions")
        lat, lon = cur.fetchone()
        assert 42.0 < lat < 43.0 and -72.0 < lon < -70.0     # Boston, not the ocean

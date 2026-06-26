"""Pytest fixtures: an isolated, disposable test database.

Creates `livetransit_test` (separate from the live DB), with just the
vehicle_positions table + dedupe index, then drops it. Uses sync psycopg (no async
event-loop concerns). Skips cleanly if Postgres isn't reachable.
"""
import psycopg
import pytest

from backend.app.core import config

TEST_DB = "livetransit_test"


def _base() -> str:
    """The DATABASE_URL up to host:port (without the database name)."""
    return config.DATABASE_URL.rsplit("/", 1)[0]


@pytest.fixture
def db():
    if not config.DATABASE_URL:
        pytest.skip("DATABASE_URL not set")
    try:
        admin = psycopg.connect(_base() + "/postgres", autocommit=True)
    except Exception as exc:  # postgres not running -> skip (unit tests still run)
        pytest.skip(f"postgres not reachable: {exc}")

    with admin.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        cur.execute(f"CREATE DATABASE {TEST_DB}")
    admin.close()

    conn = psycopg.connect(_base() + f"/{TEST_DB}", autocommit=True)
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        cur.execute(
            """CREATE TABLE vehicle_positions (
                id BIGSERIAL, vehicle_id TEXT, trip_id TEXT, route_id TEXT,
                latitude DOUBLE PRECISION, longitude DOUBLE PRECISION,
                geom geometry(Point, 4326), bearing DOUBLE PRECISION,
                recorded_at TIMESTAMPTZ, ingested_at TIMESTAMPTZ DEFAULT now(),
                h3_cell TEXT)"""
        )
        cur.execute(
            "CREATE UNIQUE INDEX vp_dedupe ON vehicle_positions "
            "(vehicle_id, recorded_at) NULLS NOT DISTINCT"
        )
    yield conn
    conn.close()

    admin = psycopg.connect(_base() + "/postgres", autocommit=True)
    with admin.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    admin.close()

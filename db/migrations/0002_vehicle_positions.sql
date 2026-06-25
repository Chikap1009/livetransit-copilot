-- db/migrations/0002_vehicle_positions.sql
-- Live vehicle positions from the MBTA GTFS-Realtime VehiclePositions feed (Phase 1).
-- Intentionally minimal: NO dedup, H3, TimescaleDB, or indexes yet.
--   * dedup + H3 + spatial index -> Phase 2
--   * Timescale hypertable + retention -> Phase 5
-- We expect duplicate rows each poll tick for now (fixed in Phase 2).

CREATE TABLE vehicle_positions (
    id          BIGSERIAL PRIMARY KEY,         -- auto-incrementing surrogate key
    vehicle_id  TEXT,                          -- the physical vehicle
    trip_id     TEXT,                          -- which scheduled trip it's running
    route_id    TEXT,                          -- which line
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    geom        geometry(Point, 4326),         -- (lon, lat); built on insert
    bearing     DOUBLE PRECISION,              -- heading in degrees, if provided
    recorded_at TIMESTAMPTZ,                   -- the feed's timestamp (UTC)
    ingested_at TIMESTAMPTZ DEFAULT now()      -- when our poller stored it
);

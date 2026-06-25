-- db/migrations/0001_init.sql
-- Static GTFS schema for LiveTransit Copilot (Phase 0).
-- Holds the MBTA *schedule* (the slowly-changing skeleton the live feed joins onto).
-- Spatial indexes are intentionally deferred to Phase 2 (so we can measure the speedup).

-- Enable PostGIS (the spatial extension). Required for the geometry columns below.
CREATE EXTENSION IF NOT EXISTS postgis;

-- routes: one row per transit line (subway/bus/rail).
CREATE TABLE routes (
    route_id         TEXT PRIMARY KEY,
    route_short_name TEXT,
    route_long_name  TEXT,
    route_type       INTEGER,        -- 0=tram,1=subway,2=rail,3=bus,4=ferry,...
    route_color      TEXT,           -- hex without '#', e.g. 'DA291C' (Red Line)
    route_text_color TEXT
);

-- stops: one row per stop/station, with a real PostGIS spatial point.
CREATE TABLE stops (
    stop_id        TEXT PRIMARY KEY,
    stop_name      TEXT,
    stop_lat       DOUBLE PRECISION,
    stop_lon       DOUBLE PRECISION,
    location_type  INTEGER,          -- 0=stop/platform, 1=station, ...
    parent_station TEXT,
    geom           geometry(Point, 4326)   -- (lon, lat); filled during load
);

-- trips: one scheduled run of a route on a given service day.
CREATE TABLE trips (
    trip_id       TEXT PRIMARY KEY,
    route_id      TEXT REFERENCES routes(route_id),
    service_id    TEXT,
    trip_headsign TEXT,
    direction_id  INTEGER,
    shape_id      TEXT
);

-- stop_times: every (trip, stop) arrival. The big table. Composite primary key.
CREATE TABLE stop_times (
    trip_id        TEXT REFERENCES trips(trip_id),
    stop_id        TEXT REFERENCES stops(stop_id),
    stop_sequence  INTEGER,
    arrival_time   TEXT,             -- GTFS 'HH:MM:SS'; can exceed 24h (e.g. 25:10:00)
    departure_time TEXT,
    PRIMARY KEY (trip_id, stop_sequence)
);

-- shapes: the geographic path each route draws on the map, as one LineString.
-- (GTFS provides scattered points; the loader stitches them with ST_MakeLine.)
CREATE TABLE shapes (
    shape_id TEXT PRIMARY KEY,
    geom     geometry(LineString, 4326)
);

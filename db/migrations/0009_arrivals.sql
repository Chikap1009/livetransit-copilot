-- db/migrations/0009_arrivals.sql
-- Phase 5: table of derived ACTUAL arrival events (the ML labels).
-- One row per (trip, stop): when the vehicle actually reached the stop (nearest approach),
-- the scheduled time, and the delay in seconds (actual - scheduled).

CREATE TABLE vehicle_arrivals (
    trip_id       TEXT,
    stop_id       TEXT,
    stop_sequence INTEGER,
    route_id      TEXT,
    arrived_at    TIMESTAMPTZ,    -- actual: timestamp of closest approach
    scheduled_ts  TIMESTAMPTZ,    -- scheduled arrival as an absolute timestamp
    delay_seconds INTEGER,        -- arrived_at - scheduled_ts (the label; +late, -early)
    dist_m        INTEGER,        -- how close the vehicle got (sanity check)
    PRIMARY KEY (trip_id, stop_id)
);

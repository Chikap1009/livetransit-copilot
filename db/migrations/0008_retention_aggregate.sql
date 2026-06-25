-- db/migrations/0008_retention_aggregate.sql
-- Phase 5: bound storage (retention) + keep a cheap rolling summary (continuous aggregate).

-- 1) Retention: auto-drop raw position chunks older than 72h (keeps storage bounded).
SELECT add_retention_policy('vehicle_positions', INTERVAL '72 hours');

-- 2) Continuous aggregate: per-route, per-hour activity. Incrementally maintained, and it
--    SURVIVES retention (the rollup persists even after the raw rows are dropped).
--    (count(DISTINCT ...) isn't allowed in continuous aggregates, so we count reports.)
CREATE MATERIALIZED VIEW route_activity_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', recorded_at) AS bucket,
    route_id,
    count(*)        AS position_reports,
    avg(bearing)    AS avg_bearing
FROM vehicle_positions
GROUP BY bucket, route_id
WITH NO DATA;

-- Refresh recent buckets automatically (leaves the in-progress hour alone via end_offset).
SELECT add_continuous_aggregate_policy('route_activity_hourly',
    start_offset      => INTERVAL '6 hours',
    end_offset        => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

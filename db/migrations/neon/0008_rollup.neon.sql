-- db/migrations/neon/0008_rollup.neon.sql
-- Neon variant of 0008. Neon runs the APACHE-licensed TimescaleDB build, which does NOT
-- include retention policies, continuous aggregates, or the job scheduler (those are TSL
-- "community" features). So here:
--   * the rolling summary is a PLAIN materialized view (refreshed by the app's maintenance loop)
--   * retention is handled by the app calling drop_chunks() (Apache-safe) on an interval
-- Scheduling lives in the FastAPI maintenance loop (backend/app/main.py), gated by
-- DB_MAINTENANCE_ENABLED, since Neon's pg_cron is pinned to the 'postgres' database and the
-- TimescaleDB TSL job scheduler is unavailable on the apache build.
-- The hypertable itself (migration 0007) IS Apache-safe and already applied.

-- Per-route, per-hour activity rollup. Plain matview (no timescaledb.continuous).
-- (count(DISTINCT ...) is fine in a plain matview, but we keep parity with the original.)
CREATE MATERIALIZED VIEW IF NOT EXISTS route_activity_hourly AS
SELECT
    time_bucket('1 hour', recorded_at) AS bucket,
    route_id,
    count(*)        AS position_reports,
    avg(bearing)    AS avg_bearing
FROM vehicle_positions
GROUP BY bucket, route_id
WITH NO DATA;

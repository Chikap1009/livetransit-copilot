-- db/migrations/0010_arrival_job.sql
-- Phase 5: make arrival collection automatic + multi-day safe.
--   1) Add service_date so the same trip on different days is distinct.
--   2) A stored procedure with the derivation logic.
--   3) A TimescaleDB scheduled job that runs it every 10 minutes (hands-free collection).

-- 1) service_date + new composite key
ALTER TABLE vehicle_arrivals ADD COLUMN IF NOT EXISTS service_date DATE;
UPDATE vehicle_arrivals
   SET service_date = (arrived_at AT TIME ZONE 'America/New_York')::date
 WHERE service_date IS NULL;
ALTER TABLE vehicle_arrivals ALTER COLUMN service_date SET NOT NULL;
ALTER TABLE vehicle_arrivals DROP CONSTRAINT vehicle_arrivals_pkey;
ALTER TABLE vehicle_arrivals ADD PRIMARY KEY (trip_id, stop_id, service_date);

-- 2) derivation as a procedure (single source of truth; manual runs just CALL it)
CREATE OR REPLACE PROCEDURE derive_arrivals(job_id INT DEFAULT 0, config JSONB DEFAULT NULL)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO vehicle_arrivals
        (trip_id, stop_id, stop_sequence, route_id, arrived_at,
         scheduled_ts, delay_seconds, dist_m, service_date)
    SELECT DISTINCT ON (vp.trip_id, st.stop_id, svc.service_date)
        vp.trip_id, st.stop_id, st.stop_sequence, vp.route_id,
        vp.recorded_at,
        sched.scheduled_ts,
        EXTRACT(EPOCH FROM (vp.recorded_at - sched.scheduled_ts))::int,
        ST_Distance(vp.geom::geography, s.geom::geography)::int,
        svc.service_date
    FROM vehicle_positions vp
    JOIN stop_times st ON st.trip_id = vp.trip_id AND st.arrival_time <> ''
    JOIN stops s       ON s.stop_id = st.stop_id
    CROSS JOIN LATERAL (
        SELECT (vp.recorded_at AT TIME ZONE 'America/New_York')::date AS service_date
    ) svc
    CROSS JOIN LATERAL (
        SELECT ((svc.service_date::timestamp AT TIME ZONE 'America/New_York')
                + st.arrival_time::interval) AS scheduled_ts
    ) sched
    WHERE vp.recorded_at >= now() - interval '2 hours'
      AND ST_DWithin(vp.geom::geography, s.geom::geography, 75)
    ORDER BY vp.trip_id, st.stop_id, svc.service_date,
             ST_Distance(vp.geom::geography, s.geom::geography)
    ON CONFLICT (trip_id, stop_id, service_date) DO NOTHING;
END;
$$;

-- 3) run it automatically every 10 minutes
SELECT add_job('derive_arrivals', INTERVAL '10 minutes');

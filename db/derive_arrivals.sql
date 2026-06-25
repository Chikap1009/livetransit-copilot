-- db/derive_arrivals.sql
-- Detect actual arrivals from recent positions and upsert them into vehicle_arrivals.
-- Run periodically (manually for now; a scheduled job later). Idempotent via ON CONFLICT.
--
-- Method: for each (trip, scheduled stop), take the position of CLOSEST APPROACH within 75 m
-- (DISTINCT ON ... ORDER BY distance). The scheduled time is the GTFS local arrival_time placed
-- on the service date (America/New_York) and converted to an absolute timestamp.

INSERT INTO vehicle_arrivals
    (trip_id, stop_id, stop_sequence, route_id, arrived_at, scheduled_ts, delay_seconds, dist_m)
SELECT DISTINCT ON (vp.trip_id, st.stop_id)
    vp.trip_id,
    st.stop_id,
    st.stop_sequence,
    vp.route_id,
    vp.recorded_at AS arrived_at,
    sched.scheduled_ts,
    EXTRACT(EPOCH FROM (vp.recorded_at - sched.scheduled_ts))::int AS delay_seconds,
    ST_Distance(vp.geom::geography, s.geom::geography)::int AS dist_m
FROM vehicle_positions vp
JOIN stop_times st ON st.trip_id = vp.trip_id AND st.arrival_time <> ''
JOIN stops s       ON s.stop_id = st.stop_id
CROSS JOIN LATERAL (
    SELECT ((((vp.recorded_at AT TIME ZONE 'America/New_York')::date)::timestamp
             AT TIME ZONE 'America/New_York') + st.arrival_time::interval) AS scheduled_ts
) sched
WHERE vp.recorded_at >= now() - interval '2 hours'
  AND ST_DWithin(vp.geom::geography, s.geom::geography, 75)
ORDER BY vp.trip_id, st.stop_id, ST_Distance(vp.geom::geography, s.geom::geography)
ON CONFLICT (trip_id, stop_id) DO NOTHING;

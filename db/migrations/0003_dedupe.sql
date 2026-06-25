-- db/migrations/0003_dedupe.sql
-- Phase 2: make ingestion idempotent.
-- The dedupe key is (vehicle_id, recorded_at): one physical vehicle reports one
-- position per timestamp. A UNIQUE index lets the processor INSERT ... ON CONFLICT
-- DO NOTHING, so re-processing the same item is harmless.
--
-- NULLS NOT DISTINCT (Postgres 15+) treats NULL recorded_at values as equal too,
-- so vehicles missing a timestamp still dedupe instead of piling up.

-- Clear the throwaway Phase 1 test rows (which contain duplicates) so the unique
-- index can be created cleanly. Real history collection restarts after this.
TRUNCATE vehicle_positions;

CREATE UNIQUE INDEX vehicle_positions_dedupe
    ON vehicle_positions (vehicle_id, recorded_at) NULLS NOT DISTINCT;

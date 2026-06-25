-- db/migrations/0007_timescale.sql
-- Phase 5: turn vehicle_positions into a TimescaleDB hypertable (time-partitioned by
-- recorded_at). A hypertable's time column must be NOT NULL, and every unique index
-- must include it -- so we drop the surrogate id primary key and rely on the existing
-- (vehicle_id, recorded_at) dedupe index, which already includes the time column.

ALTER TABLE vehicle_positions ALTER COLUMN recorded_at SET NOT NULL;
ALTER TABLE vehicle_positions DROP CONSTRAINT vehicle_positions_pkey;

CREATE EXTENSION IF NOT EXISTS timescaledb;
SELECT create_hypertable('vehicle_positions', 'recorded_at', migrate_data => true);

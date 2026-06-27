-- db/migrations/0011_stop_times_stop_idx.sql
-- Trip planning (Phase C finale) looks up stop_times by stop_id a lot:
--   "which trips serve this stop, in what sequence, at what time?"
-- stop_times has 3.3M rows and only a PRIMARY KEY on (trip_id, stop_sequence),
-- so filtering by stop_id alone forces a full sequential scan every time.
-- A B-tree index on stop_id turns those lookups into fast index scans
-- (same lesson as the Phase 2 GiST index, applied to a plain B-tree column).
CREATE INDEX IF NOT EXISTS stop_times_stop_id_idx ON stop_times (stop_id);

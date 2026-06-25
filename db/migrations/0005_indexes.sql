-- db/migrations/0005_indexes.sql
-- Phase 2: spatial + neighborhood indexes (and MEASURE the speedup with EXPLAIN ANALYZE).
--   * GiST on geom -> "vehicles within distance" switches from Seq Scan to Index Scan.
--   * B-tree on h3_cell -> fast neighborhood (cell equality) lookups.

CREATE INDEX vehicle_positions_geom_gist ON vehicle_positions USING GIST (geom);
CREATE INDEX vehicle_positions_h3_idx    ON vehicle_positions (h3_cell);

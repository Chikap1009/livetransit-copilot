-- db/migrations/0004_h3.sql
-- Phase 2: tag each vehicle position with its H3 hexagon cell (resolution 8,
-- ~0.74 km^2 ≈ a neighborhood). Enables instant "vehicles near me" grouping via a
-- plain equality match on h3_cell, with no geometry math. Stored as the H3 hex id
-- string (e.g. '882a306603fffff'). A B-tree index is added in the next sub-step.

ALTER TABLE vehicle_positions ADD COLUMN h3_cell TEXT;

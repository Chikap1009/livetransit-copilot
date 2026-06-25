-- db/migrations/0006_route_shapes.sql
-- Phase 4: a view that attaches each route's color to its shape geometry, so the
-- tile server (Martin) can publish colored route lines. shapes <- trips -> routes.
-- DISTINCT ON (shape_id) keeps one route per shape; route_color gets a '#' prefix
-- (GTFS stores it without one) with a grey fallback when blank.

CREATE VIEW route_shapes AS
SELECT DISTINCT ON (s.shape_id)
    s.shape_id,
    t.route_id,
    '#' || COALESCE(NULLIF(r.route_color, ''), '888888') AS route_color,
    r.route_type,
    s.geom
FROM shapes s
JOIN trips t  ON t.shape_id = s.shape_id
JOIN routes r ON r.route_id = t.route_id;

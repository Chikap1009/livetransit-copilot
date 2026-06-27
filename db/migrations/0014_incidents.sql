-- db/migrations/0014_incidents.sql
-- Phase F: the Network Watchdog's incident reports.
-- Cheap anomaly detection (SQL) finds candidates; the Watchdog agent investigates
-- and writes a human-readable IncidentReport stored here.

CREATE TABLE incidents (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind        TEXT NOT NULL,                 -- 'bunching' | 'delay' | 'gap'
    route_id    TEXT,
    severity    TEXT NOT NULL DEFAULT 'medium',-- 'low' | 'medium' | 'high'
    summary     TEXT NOT NULL,                 -- the Watchdog's report text
    evidence    JSONB NOT NULL DEFAULT '{}',   -- the raw anomaly data it reasoned over
    fingerprint TEXT,                          -- dedupe the same ongoing anomaly
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Newest-first listing for the UI panel.
CREATE INDEX incidents_recent_idx ON incidents (created_at DESC);

-- Dedupe lookups: "is there already a recent incident for this kind/route/fingerprint?"
CREATE INDEX incidents_dedup_idx ON incidents (kind, route_id, fingerprint, created_at DESC);

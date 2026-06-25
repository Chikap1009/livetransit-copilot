-- db/derive_arrivals.sql
-- Manually trigger one arrival-derivation pass. The logic lives in the derive_arrivals()
-- procedure (see migration 0010); a TimescaleDB job also runs it every 10 minutes.
CALL derive_arrivals();

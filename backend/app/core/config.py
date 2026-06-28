"""Central configuration: loads the project .env and exposes settings as constants.

Keeping config in one place (and out of the code) is the discipline from Part 0 rule #7:
secrets live in .env, code reads them here.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = three levels up from this file (backend/app/core/config.py -> root).
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

# --- Database / cache ---
# Optional at import time: not every process needs the DB (e.g. the poller only
# publishes to Redis). Components that need it read it and connect explicitly.
DATABASE_URL = os.environ.get("DATABASE_URL")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# --- MBTA GTFS-Realtime feed ---
MBTA_VEHICLE_POSITIONS_URL = os.environ.get(
    "MBTA_VEHICLE_POSITIONS_URL",
    "https://cdn.mbta.com/realtime/VehiclePositions.pb",
)

# How often the poller fetches the feed (seconds).
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "10"))

# H3 hexagon resolution for tagging positions (8 ≈ 0.74 km^2, neighborhood-sized).
H3_RESOLUTION = int(os.environ.get("H3_RESOLUTION", "8"))

# --- Network Watchdog (Phase F) ---
# Background anomaly-monitoring loop is OFF by default (it uses LLM quota). Enable with
# WATCHDOG_ENABLED=true; it then runs every WATCHDOG_INTERVAL_SECONDS.
WATCHDOG_ENABLED = os.environ.get("WATCHDOG_ENABLED", "false").lower() in ("1", "true", "yes")
WATCHDOG_INTERVAL_SECONDS = int(os.environ.get("WATCHDOG_INTERVAL_SECONDS", "900"))

# --- Agent rate limiting (Phase H) ---
# Max agent requests per minute per client IP (a public free-tier agent must not let one
# user drain the quota). 0 disables the limit.
AGENT_RATE_LIMIT_PER_MIN = int(os.environ.get("AGENT_RATE_LIMIT_PER_MIN", "20"))

# --- CORS (Phase J) ---
# Comma-separated allowed origins for the browser frontend (e.g. the Cloudflare Pages URL).
# Default "*" is convenient for local/dev; in production set it to the exact Pages origin(s).
CORS_ALLOW_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()
]

# --- DB maintenance loop (Phase J) ---
# Neon runs the APACHE-licensed TimescaleDB (no retention policies / continuous-aggregate
# policies / add_job) and its pg_cron is pinned to another database. So in production the
# API process runs these jobs itself on an interval. OFF by default (local docker uses the
# real TimescaleDB scheduler instead).
DB_MAINTENANCE_ENABLED = os.environ.get("DB_MAINTENANCE_ENABLED", "false").lower() in (
    "1", "true", "yes",
)
DB_MAINTENANCE_INTERVAL_SECONDS = int(os.environ.get("DB_MAINTENANCE_INTERVAL_SECONDS", "600"))
# Drop raw position chunks fully older than this (bounds storage on the 0.5 GB free tier).
DB_RETENTION_INTERVAL = os.environ.get("DB_RETENTION_INTERVAL", "90 minutes")

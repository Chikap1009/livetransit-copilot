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

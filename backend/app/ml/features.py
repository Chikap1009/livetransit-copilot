"""Build the ML training set from derived arrivals (delay-propagation framing).

Each row = one arrival (the target) paired with the delay at the PREVIOUS stop on the
same trip (current_delay), plus time/route context. All features are knowable before
reaching the target stop (no leakage). Bad labels are filtered out.

CLI:  .venv\\Scripts\\python.exe -m backend.app.ml.features
"""
import pandas as pd
import psycopg

from backend.app.core import config

MAX_ABS_DELAY = 1800   # drop labels worse than +/-30 min (bad derivations)
MAX_DIST_M = 60        # require a close stop approach

FEATURE_SQL = f"""
    SELECT
        a.scheduled_ts,
        a.route_id,
        a.stop_sequence,
        prev.delay_seconds AS current_delay,
        EXTRACT(hour FROM a.scheduled_ts AT TIME ZONE 'America/New_York')::int AS hour,
        EXTRACT(dow  FROM a.scheduled_ts AT TIME ZONE 'America/New_York')::int AS dow,
        a.delay_seconds AS target_delay
    FROM vehicle_arrivals a
    JOIN LATERAL (
        -- the most recent earlier stop on the same trip+day (the "current" delay)
        SELECT p.delay_seconds
        FROM vehicle_arrivals p
        WHERE p.trip_id = a.trip_id
          AND p.service_date = a.service_date
          AND p.stop_sequence < a.stop_sequence
          AND abs(p.delay_seconds) <= {MAX_ABS_DELAY}
        ORDER BY p.stop_sequence DESC
        LIMIT 1
    ) prev ON true
    WHERE abs(a.delay_seconds) <= {MAX_ABS_DELAY}
      AND a.dist_m < {MAX_DIST_M}
    ORDER BY a.scheduled_ts
"""

FEATURES = ["current_delay", "hour", "dow", "stop_sequence", "route_id"]
TARGET = "target_delay"


def build_dataset() -> pd.DataFrame:
    """Return a time-ordered DataFrame of features + target."""
    with psycopg.connect(config.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(FEATURE_SQL)
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols)
    for c in ["stop_sequence", "current_delay", "hour", "dow", "target_delay"]:
        df[c] = pd.to_numeric(df[c])
    df["route_id"] = df["route_id"].astype("category")
    return df


if __name__ == "__main__":
    df = build_dataset()
    print(f"rows: {len(df):,}   routes: {df['route_id'].nunique()}")
    print(f"time span: {df['scheduled_ts'].min()}  ->  {df['scheduled_ts'].max()}")
    print("\ntarget_delay (s):")
    print(df["target_delay"].describe().round(1).to_string())
    print("\ncurrent_delay (s):")
    print(df["current_delay"].describe().round(1).to_string())
    corr = df["current_delay"].corr(df["target_delay"])
    print(f"\ncorr(current_delay, target_delay) = {corr:.3f}")
    print("\nsample:")
    print(df.drop(columns=["scheduled_ts"]).head(6).to_string(index=False))

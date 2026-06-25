"""Load MBTA static GTFS (the schedule) from data/MBTA_GTFS.zip into PostGIS.

Re-runnable: truncates the GTFS tables first, then bulk-loads with COPY.
Run:  .venv\\Scripts\\python.exe db/load_static_gtfs.py
"""
import csv
import io
import os
import zipfile
from pathlib import Path

import psycopg

ZIP_PATH = Path("data/MBTA_GTFS.zip")


def load_env(path: str = ".env") -> None:
    """Tiny .env reader so we don't add a dependency. Sets os.environ."""
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def rows(zf: zipfile.ZipFile, name: str):
    """Yield each CSV row of a GTFS file as a dict (handles a UTF-8 BOM)."""
    with zf.open(name) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        yield from csv.DictReader(text)


def num(value):
    """Empty string -> None, else float (for lat/lon columns that may be blank)."""
    return float(value) if value not in (None, "") else None


def integer(value):
    """Empty string -> None, else int (for integer columns that may be blank)."""
    return int(value) if value not in (None, "") else None


def main() -> None:
    load_env()
    dsn = os.environ["DATABASE_URL"]
    with zipfile.ZipFile(ZIP_PATH) as zf, psycopg.connect(dsn) as conn:
        cur = conn.cursor()

        # 1) Start clean so the script is idempotent (safe to re-run).
        cur.execute("TRUNCATE stop_times, trips, shapes, stops, routes CASCADE;")

        # 2) routes
        with cur.copy(
            "COPY routes (route_id, route_short_name, route_long_name, "
            "route_type, route_color, route_text_color) FROM STDIN"
        ) as cp:
            for r in rows(zf, "routes.txt"):
                cp.write_row((
                    r["route_id"], r["route_short_name"], r["route_long_name"],
                    integer(r["route_type"]), r["route_color"], r["route_text_color"],
                ))

        # 3) stops (raw columns first; the spatial point is built afterwards)
        with cur.copy(
            "COPY stops (stop_id, stop_name, stop_lat, stop_lon, "
            "location_type, parent_station) FROM STDIN"
        ) as cp:
            for r in rows(zf, "stops.txt"):
                cp.write_row((
                    r["stop_id"], r["stop_name"], num(r["stop_lat"]),
                    num(r["stop_lon"]), integer(r.get("location_type")),
                    r.get("parent_station") or None,
                ))
        # Build the PostGIS point — note lon FIRST: ST_MakePoint(lon, lat).
        cur.execute(
            "UPDATE stops SET geom = ST_SetSRID(ST_MakePoint(stop_lon, stop_lat), 4326) "
            "WHERE stop_lat IS NOT NULL AND stop_lon IS NOT NULL;"
        )

        # 4) trips
        with cur.copy(
            "COPY trips (trip_id, route_id, service_id, trip_headsign, "
            "direction_id, shape_id) FROM STDIN"
        ) as cp:
            for r in rows(zf, "trips.txt"):
                cp.write_row((
                    r["trip_id"], r["route_id"], r["service_id"],
                    r["trip_headsign"], integer(r.get("direction_id")),
                    r.get("shape_id") or None,
                ))

        # 5) stop_times (the big table — COPY makes this fast)
        with cur.copy(
            "COPY stop_times (trip_id, stop_id, stop_sequence, "
            "arrival_time, departure_time) FROM STDIN"
        ) as cp:
            for r in rows(zf, "stop_times.txt"):
                cp.write_row((
                    r["trip_id"], r["stop_id"], integer(r["stop_sequence"]),
                    r["arrival_time"] or None, r["departure_time"] or None,
                ))

        # 6) shapes: stage raw points, then stitch into LineStrings inside PostGIS.
        cur.execute(
            "CREATE TEMP TABLE shape_pts (shape_id TEXT, lat FLOAT, lon FLOAT, seq INT);"
        )
        with cur.copy("COPY shape_pts (shape_id, lat, lon, seq) FROM STDIN") as cp:
            for r in rows(zf, "shapes.txt"):
                cp.write_row((
                    r["shape_id"], num(r["shape_pt_lat"]),
                    num(r["shape_pt_lon"]), integer(r["shape_pt_sequence"]),
                ))
        cur.execute(
            "INSERT INTO shapes (shape_id, geom) "
            "SELECT shape_id, "
            "ST_MakeLine(ST_SetSRID(ST_MakePoint(lon, lat), 4326) ORDER BY seq) "
            "FROM shape_pts GROUP BY shape_id HAVING COUNT(*) >= 2;"
        )

        conn.commit()

        # 7) report row counts
        print("Loaded:")
        for table in ("routes", "stops", "trips", "stop_times", "shapes"):
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            print(f"  {table:12} {cur.fetchone()[0]:>10,}")


if __name__ == "__main__":
    main()

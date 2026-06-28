#!/usr/bin/env bash
# ops/deploy/init_db.sh — one-time database bootstrap on the deploy host.
#
# Applies all migrations against the running Postgres container (full TimescaleDB, so the
# original 0001..0014 incl. the TSL retention/continuous-aggregate/add_job jobs all apply),
# then loads the static GTFS schedule from data/MBTA_GTFS.zip.
#
# Prereqs: the stack is up (`docker compose up -d postgres redis api poller processor tiles`),
# a filled-in `.env` exists at the repo root, and data/MBTA_GTFS.zip is present.
#
# Run from anywhere:  bash ops/deploy/init_db.sh
set -euo pipefail
cd "$(dirname "$0")/../.."            # -> repo root
set -a; source .env; set +a

PSQL="docker compose exec -T -e PGPASSWORD=$POSTGRES_PASSWORD postgres \
      psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB"

echo ">> Applying migrations (full TimescaleDB) ..."
for f in db/migrations/0*.sql; do
  printf '   %-46s' "$f"
  $PSQL -q < "$f" >/dev/null && echo OK
done

echo ">> Loading static GTFS (reads data/MBTA_GTFS.zip) ..."
docker compose run --rm -v "$PWD:/repo" -w /repo api python db/load_static_gtfs.py

echo ">> Row counts:"
$PSQL -c "SELECT 'routes' AS table, count(*) FROM routes \
          UNION ALL SELECT 'stops', count(*) FROM stops \
          UNION ALL SELECT 'trips', count(*) FROM trips \
          UNION ALL SELECT 'stop_times', count(*) FROM stop_times;"
echo ">> DB bootstrap complete."

# LiveTransit Copilot — Build Log

> A running, detailed record of **everything** we do in this project, with plain-language
> explanations of *what* was done, *why*, and *how it was verified*. Appended to after every
> prompt so we never lose context. Newest entries go at the bottom.
>
> Audience: me (a B.Tech student learning backend + agentic AI). Written so I can re-read it
> later and understand every decision.

---

## Entry 0 — Project kickoff & prerequisite check
**Date:** 2026-06-25
**Phase:** Pre-Phase 0 (setup)

### What we did
1. **Read the entire Build Bible** (`LiveTransit_Copilot_Build_Bible.md`, 878 lines, Parts 0–8).
   This document is our single source of truth: spec + concept textbook + phase-by-phase plan.
2. **Acknowledged the Part 0 working rules** — the core discipline for the whole project:
   explain-before-execute, one concept at a time, define jargon with analogies, give a
   verification step after every action, never commit secrets, quiz at the end of each phase.
3. **Took a prerequisite inventory** (Part 4).
   - Local tools the user already has: **Git, Docker Desktop, Python 3.11+, Node.js 20+**.
   - Accounts already created: **GitHub** + **GitHub Student Developer Pack** (the slow-approval
     one — applied early, good).
   - Not needed yet (later phases): Neon/Upstash/Cloudflare (Phase J deploy), LLM provider
     keys + Langfuse (Phase A onward).

### Verification run (read-only version checks)
Ran: `git --version; docker --version; docker compose version; python --version; node --version; docker ps`

Results:
| Tool | Found | Required | Status |
|---|---|---|---|
| Git | 2.52.0 | any recent | ✅ |
| Docker (CLI) | 29.4.2 | any recent | ✅ |
| Docker Compose | v5.1.3 | v2+ | ✅ |
| Python | 3.14.2 | 3.11+ | ✅ (but see note) |
| Node.js | 24.12.0 | 20+ | ✅ |
| Docker **engine** | NOT running | must be running | ❌ daemon not up |

### Open issues / notes to revisit
- **Docker engine not running.** `docker ps` failed with
  "failed to connect to the docker API ... daemon running?". The Docker *CLI* is installed but
  Docker *Desktop* (which hosts the actual engine on WSL2) isn't started. **Fix:** launch Docker
  Desktop and wait for it to say "Engine running", then re-run `docker ps`. This must be green
  before Phase 0's `docker compose up`.
- **Python 3.14 is very new.** The floor (3.11+) is met, but 3.14 is bleeding-edge; some compiled
  dependencies (e.g. LightGBM) may not yet ship prebuilt wheels for it. Most backend code runs
  *inside Docker* (where we pin the Python version), so this mostly affects local tooling. Flagged
  to revisit if/when a local `pip install` fails — we may use a 3.11/3.12 virtual environment then.

### Decision: created this build log
At the user's request, created `BUILD_LOG.md` (this file) to maintain context across the whole
chat. Every future prompt will append a detailed, explained entry here.

### Next step
Get the Docker engine running (start Docker Desktop), verify `docker ps` succeeds, then begin
**Phase 0** (repo + docker-compose stack with Postgres/PostGIS + Redis + MBTA static GTFS).

---

## Entry 1 — Docker engine confirmed; port-conflict flagged
**Date:** 2026-06-25
**Phase:** Pre-Phase 0 (setup)

### What we did
- User started Docker Desktop. Re-ran `docker ps` + `docker version`.
- **Engine is now running:** Server **29.5.3**, OS/Arch **linux/amd64** (via WSL2). ✅
  All prerequisites are now satisfied — Phase 0 is unblocked.

### Important finding: pre-existing containers from another project
`docker ps` showed three running containers belonging to a separate project (`pathfinder`):
| Container | Image | Host port(s) |
|---|---|---|
| `pathfinder-redis` | redis:7-alpine | **6379** |
| `pathfinder-qdrant` | qdrant/qdrant | 6333–6334 |
| `pathfinder-neo4j` | neo4j:5-community | 7474, 7687 |

**Why this matters:** our Phase 0 stack runs its own Redis, whose default host port is **6379** —
already held by `pathfinder-redis`. A port can only be held by one program at a time, so mapping
our Redis to 6379 would fail with "port already allocated."

**Two options presented to the user (awaiting decision):**
1. *(recommended, non-destructive)* Leave pathfinder running; map our Redis to a different host
   port, e.g. `6380:6379`. Both projects coexist.
2. Stop the pathfinder containers (reversible; data volumes preserved) and use the standard 6379.

**Rule honored:** will NOT touch the pathfinder containers without explicit user permission — they
belong to a different project.

### Next step
Get the user's choice on the Redis port question, then start **Phase 0**: create repo + `.gitignore`
+ stub README → `docker-compose.yml` (PostGIS image + Redis + named volume) → `.env`/`.env.example`
→ init migration for static GTFS tables → load MBTA static GTFS → verify with a spatial query.

---

## Entry 2 — Phase 0, Step 1: git repo + .gitignore + stub README
**Date:** 2026-06-25
**Phase:** Phase 0 (foundations)

### Decision made
User authorized **stopping the pathfinder containers** (Option 2). Ran
`docker stop pathfinder-redis pathfinder-qdrant pathfinder-neo4j`. All three stopped; `docker ps`
now empty; **port 6379 is free** so our Redis can use the standard port. Pathfinder data volumes
untouched — restart with `docker start pathfinder-redis pathfinder-qdrant pathfinder-neo4j`.

### Concept taught: Git
Version control = "infinite labeled undo history" for the whole project (snapshots = commits;
branches = parallel experiments; GitHub = online host). We start here so every later file is
tracked from line one.

### What we did
1. **`.gitignore`** (created first, on purpose — secrets safety net). Ignores `.env`/`.env.*`
   (but keeps `.env.example`), Python caches/venvs, GTFS data dumps (`*.pb`, `*.zip`, `*.parquet`,
   `data/`), ML model binaries (`models/`, `*.lgb`), frontend build output (`node_modules/`,
   `.next/`), and editor/OS noise.
2. **`README.md`** — stub front-door (polished later in Part 6).
3. **`git init -b main`** — initialized repo on the modern default branch name `main`.
4. **First commit** `13f7bde` — "chore: initialize repo with .gitignore and stub README".
   4 files tracked: `.gitignore`, `BUILD_LOG.md`, `LiveTransit_Copilot_Build_Bible.md`, `README.md`.
   Confirmed **no `.env`** present.

### How to verify
- `git status` → "nothing to commit, working tree clean".
- `git log --oneline` → shows commit `13f7bde`.

### Notes / flags (no action needed now)
- **CRLF/LF warning** on commit: harmless Windows↔Linux line-ending normalization. Can add a
  `.gitattributes` later if noisy.
- **OneDrive location:** project sits under `OneDrive\Desktop`, which auto-syncs. Heavy build dirs
  are already git-ignored; just watch for occasional "file in use" locks later. Not a blocker.
- Have NOT created a GitHub remote / pushed yet — that's a separate, explained step (will confirm
  GitHub username + repo name first).

### Next step
**Phase 0, Step 2:** write `docker-compose.yml` defining the PostGIS container + Redis container +
a named volume for data persistence. Teach: Docker images, containers, services, ports, volumes.

---

## Entry 3 — Phase 0, Steps 2–4: docker-compose stack up & healthy
**Date:** 2026-06-25
**Phase:** Phase 0 (foundations)

### Concepts taught
- **Image vs container**: image = read-only blueprint (recipe/class); container = running instance
  (dish/object). We run prebuilt images instead of installing DBs on the laptop.
- **Images used**: `postgis/postgis:16-3.4` (Postgres 16 + PostGIS baked in) and `redis:7-alpine`.
- **docker-compose / services**: one YAML defines multiple containers, started as a group.
- **Ports**: `"5432:5432"` = host:container mapping so laptop code can reach the container.
- **Named volumes** (critical): container filesystems are ephemeral (wiped on recreate); a named
  volume persists data outside the container. Mounted `pgdata` at `/var/lib/postgresql/data`.
- **Env vars**: config/secrets passed from outside the code; real values in git-ignored `.env`,
  template in committed `.env.example`.

### What we did
1. **`docker-compose.yml`** — postgres + redis services, port maps, named volumes (`pgdata`,
   `redisdata`), healthchecks (`pg_isready`, `redis-cli ping`), `restart: unless-stopped`.
2. **Port check** — `5432` and `6379` both FREE (Get-NetTCPConnection). No conflicts.
3. **`.env`** (git-ignored, real local values) + **`.env.example`** (committed template).
   POSTGRES_USER/PASSWORD/DB + DATABASE_URL + REDIS_URL. Password is local-dev-only.
4. **Bug caught by verification (taught):** `.gitignore` inline comment broke the `!.env.example`
   negation — in gitignore, `#` only starts a comment at the START of a line; inline `#` becomes
   part of the pattern. Fixed by moving comments to their own lines. Re-verified: `.env` ignored,
   `.env.example` tracked.
5. **`docker compose up -d`** — pulled images, created network + volumes, started both containers.
6. **Verified healthy**: `docker compose ps` → both Up (healthy); `SELECT postgis_version()` →
   `3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1`; `redis-cli ping` → `PONG`.

### Note
- The `postgis/postgis` image **auto-creates the PostGIS extension** on first boot, so the Bible's
  manual `CREATE EXTENSION postgis;` was unnecessary here.

### How to verify (anytime)
- `docker compose ps` → both services "Up (healthy)".
- `docker compose exec -T postgres psql -U livetransit -d livetransit -c "SELECT postgis_version();"`
- `docker compose exec -T redis redis-cli ping` → `PONG`.
- Stop with `docker compose down` (data persists in volumes); `down -v` wipes volumes.

### Next step
**Phase 0, Step 5:** write `db/migrations/0001_init.sql` creating the static GTFS tables
(`routes`, `stops` with `geom geometry(Point,4326)`, `trips`, `stop_times`, `shapes`). Teach:
relational tables, primary/foreign keys, SRID 4326, and how GTFS CSVs map to tables.

---

## Entry 4 — Phase 0, Step 5: static GTFS schema created & applied
**Date:** 2026-06-25
**Phase:** Phase 0 (foundations)

### Concepts taught
- **Relational model**: tables/rows/columns; tables relate via shared IDs.
- **Primary key** (unique row id) / **foreign key** (points to another table's PK, enforces
  integrity). E.g. `trips.route_id → routes.route_id`; `stop_times` has composite PK
  `(trip_id, stop_sequence)`.
- **GTFS file → table mapping**: routes.txt→routes, stops.txt→stops, trips.txt→trips,
  stop_times.txt→stop_times (the big one), shapes.txt→shapes.
- **SRID 4326** = GPS lat/lon (WGS84). Stored as PostGIS `geometry(Point,4326)`. Trap: PostGIS
  points are `(x,y)` = **(lon, lat)** — longitude first. Build with `ST_MakePoint(lon, lat)`.
- **Migration** = versioned `.sql` schema-change script (numbered `0001_…`), tracked in git.

### What we did
1. Created **`db/migrations/0001_init.sql`** — 5 tables (routes, stops, trips, stop_times, shapes),
   with `stops.geom` Point/4326 and `shapes.geom` LineString/4326. Kept only columns we'll use;
   GiST indexes deferred to Phase 2 (to measure speedup).
2. Applied it: piped the file into `psql` with `ON_ERROR_STOP=1`. 5× CREATE TABLE OK.
3. Verified: `\dt` shows our 5 tables in `public`; `geometry_columns` confirms `stops.geom`
   POINT/4326 and `shapes.geom` LINESTRING/4326.
4. Committed `27fbbf0`.

### Note (avoid confusion)
`\dt` listed **42 tables** — most are from the PostGIS image's optional `postgis_tiger_geocoder`
(`tiger` schema) and `postgis_topology` (`topology` schema) extensions. **Not ours; ignore them.**
Our tables are the ones in the `public` schema. `public.spatial_ref_sys` is PostGIS's built-in
coordinate-system reference table.

### How to verify
- `docker compose exec -T postgres psql -U livetransit -d livetransit -c "\dt public.*"`
- Expect: routes, shapes, stop_times, stops, trips (+ spatial_ref_sys).

### Next step
**Phase 0, Step 6 (final):** download the MBTA static GTFS zip, write `db/load_static_gtfs.py` to
parse the CSVs and insert rows (build `stops.geom` from lon/lat; stitch `shapes` LineStrings),
then verify with row counts + a `ST_DWithin` "stops near downtown Boston" query. Then the Phase 0
Concept Check.

---

## Entry 5 — Phase 0, Step 6: MBTA schedule loaded; Phase 0 COMPLETE
**Date:** 2026-06-25
**Phase:** Phase 0 (foundations)

### Concepts taught
- **Virtual environment (`.venv`)**: project-local isolated Python so packages don't clash across
  projects. Installed `psycopg[binary]` (the `[binary]` = prebuilt wheel, no compiler needed).
  Python 3.14 worry resolved — a `cp314` wheel of psycopg 3.3.4 installed cleanly.
- **`COPY`**: PostgreSQL bulk-load path (one stream vs one round-trip per row). 10–100× faster;
  used for the big tables. Analogy: one truck vs 2M letters.
- **Shapes via aggregation**: GTFS shapes are scattered points; stitched into one LineString per
  `shape_id` with `ST_MakeLine(point ORDER BY seq)` grouped by `shape_id` (HAVING count>=2).
- **Idempotent loader**: `TRUNCATE ... CASCADE` first so re-running can't duplicate-key crash.

### What we did (6a + 6b)
1. Downloaded `data/MBTA_GTFS.zip` (24.7 MB). Inspected contents — `stop_times.txt` is 148 MB
   (the big one), `shapes.txt` 16 MB, rest small.
2. Created `.venv`; installed `psycopg[binary]==3.3.4`. Added `db/requirements.txt`.
3. Wrote `db/load_static_gtfs.py` (stdlib csv/zipfile + psycopg; no pandas).
4. **Bug #1 (caught & fixed):** `num()` made every value a float, so `route_type` "1" → "1.0",
   rejected by the INTEGER column. Added an `integer()` helper; applied to route_type,
   location_type, direction_id, stop_sequence, shape_pt_sequence.
5. Re-ran — loaded in **51.3 s**: routes **403**, stops **10,308**, trips **121,935**,
   stop_times **3,345,680**, shapes **1,150**.
6. **Payoff query:** `ST_DWithin` found stops within 500 m of downtown Boston (Government Center
   48–64 m, City Hall Plaza). Correct = stops are in Boston (not the ocean) → (lon, lat) order +
   SRID 4326 verified.
7. **Bug #2 (caught & fixed):** the GTFS section of `.gitignore` ALSO had inline comments, so
   `*.pb/*.zip/*.parquet/data/` were silently NOT ignored (the 24 MB zip was at risk of being
   committed). Moved comments to their own lines; verified `git check-ignore` now matches and no
   inline-comment patterns remain anywhere in the file.

### Commits
- `62e8ae7` GTFS loader + requirements
- `7049d64` fix .gitignore inline-comment bug (data section)
(earlier: `13f7bde` init, `fc909c0` docker stack, `27fbbf0` schema)

### How to verify Phase 0 (anytime)
- `docker compose ps` → postgres + redis Up (healthy).
- Row counts: `docker compose exec -T postgres psql -U livetransit -d livetransit -c "SELECT
  (SELECT count(*) FROM routes) routes, (SELECT count(*) FROM stops) stops, (SELECT count(*) FROM
  stop_times) stop_times;"`
- Spatial query: the `ST_DWithin` downtown query returns Government Center etc.
- `git status` clean; `.env`, `data/`, `*.zip` all untracked/ignored.

### LESSONS / recurring gotchas
- **gitignore inline comments break patterns** — hit this TWICE. Always put comments on their own
  line. Worth remembering for the whole project.
- COPY text format is strict about types: floats won't go into INTEGER columns.

### Phase 0 status: ✅ COMPLETE (pending Concept Check quiz).
Not yet done (intentionally, later phases): GiST/spatial indexes (Phase 2), TimescaleDB (Phase 5),
pgvector (Phase D), pushing the repo to GitHub remote (separate explained step).

### Next step
Phase 0 **Concept Check** quiz (rule #10), then on success proceed to **Phase 1** (poller:
fetch+decode MBTA VehiclePositions every ~10s, store, expose `GET /vehicles`).

---

## Entry 6 — Concept Check passed + pushed to GitHub
**Date:** 2026-06-25
**Phase:** Phase 0 → Phase 1 boundary

### Concept Check (rule #10) — PASSED
User answered all 4 (Docker isolation/clean-system/speed; PostGIS adds spatial types/functions;
.env git-ignored secrets vs .env.example template; SRID + lon-before-lat). Corrections made:
added "reproducibility" as Docker's headline benefit; sharpened PostGIS (geometry types + spatial
functions + indexes); corrected SRID = **Spatial Reference (System) ID** (user guessed "port id"),
4326 = WGS84 GPS lat/lon. Coordinate-order trap (lon, lat) recalled correctly.

### GitHub push
- Git identity on commits: `Chikap1009 <chiragkapoor1009@gmail.com>`.
- Created **public** repo via github.com (empty, no auto-init to avoid history collision).
- `git remote add origin https://github.com/Chikap1009/livetransit-copilot.git`
- `git push -u origin main` — succeeded (credentials cached; no manual login needed).
- Verified: `main...origin/main` in sync; 9 tracked files on GitHub; **`.env` NOT tracked**
  (`git ls-files --error-unmatch .env` errors = good). Repo: https://github.com/Chikap1009/livetransit-copilot

### Next step
**Phase 1** — the live poller. Goal: fetch MBTA VehiclePositions `.pb` every ~10s, decode the
protobuf with `gtfs-realtime-bindings`, store positions, expose `GET /vehicles` + `GET /health`
via FastAPI. Learn first: HTTP, REST, protobuf, poller-as-separate-process, GTFS-RT.

---

## Entry 7 — Phase 1, Sub-steps 1–2: backend skeleton + working poller
**Date:** 2026-06-25
**Phase:** Phase 1 (first ingestion)

### Concepts taught
- **GTFS-RT**: live feeds (VehiclePositions / TripUpdates / Alerts); we use VehiclePositions
  `.pb` (no key). **Protobuf**: compact binary; needs schema + `gtfs-realtime-bindings` to decode.
- **Poller vs API**: a long-lived background worker fetches the feed on a loop, separate from the
  request-handling API (background work vs request handling).
- **async/await**: cooperative multitasking — `await` a slow op (network/DB) without freezing the
  thread. Analogy: an async waiter serves other tables while food cooks.

### What we did
**Sub-step 1 (skeleton):**
- Installed backend deps (fastapi 0.138.0, uvicorn 0.49.0, httpx 0.28.1, gtfs-realtime-bindings
  2.0.0, + protobuf, pydantic, python-dotenv). Pinned in `backend/requirements.txt`.
- Created `backend/app/` package; `core/config.py` loads `.env` via python-dotenv and exposes
  DATABASE_URL, REDIS_URL, MBTA_VEHICLE_POSITIONS_URL, POLL_INTERVAL_SECONDS. Added the two MBTA
  vars to `.env` + `.env.example`.
- Migration `0002_vehicle_positions.sql` applied: table with geom Point/4326 (no dedup/H3/index).

**Sub-step 2 (poller):** `backend/app/ingest/poller.py`
- Loop: fetch `.pb` (httpx async) -> decode (gtfs_realtime_pb2) -> `executemany` INSERT building
  geom via `ST_SetSRID(ST_MakePoint(lon,lat),4326)` -> commit -> sleep to interval. try/except
  around each tick so it survives feed failures. `--ticks N` for bounded test runs.
- **Bug (Windows-specific, caught & fixed):** psycopg async cannot use Windows' default
  ProactorEventLoop. Added a `run()` helper that uses `loop_factory=asyncio.SelectorEventLoop` on
  win32 only (no-op on Linux/Docker). Used modern loop_factory (not deprecated
  set_event_loop_policy).
- Verified: `--ticks 2` stored 524 then 525 positions; DB has 1049 rows / 525 distinct vehicles
  (duplication expected, no dedup yet); sample coords ~(42.3, -71.0) Boston; geom matches lat/lon
  (correct order); top routes Red/Orange/Green/66/1.

### How to verify
- `.venv\Scripts\python.exe -m backend.app.ingest.poller --ticks 2` → logs "stored N positions".
- `docker compose exec -T postgres psql -U livetransit -d livetransit -c "SELECT count(*),
  count(DISTINCT vehicle_id) FROM vehicle_positions;"`

### Recurring gotcha added
- **Windows + psycopg async** needs SelectorEventLoop. Conditional on `sys.platform == 'win32'`.

### Next step
**Phase 1, Sub-step 3:** the API — `GET /vehicles` (latest position per vehicle) + `GET /health`
with FastAPI; run with uvicorn. Teach: HTTP request/response, REST, FastAPI routing, async DB
query. Then Sub-step 4: containerize poller + API as compose services.

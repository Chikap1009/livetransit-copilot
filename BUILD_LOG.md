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

---

## Entry 8 — Phase 1, Sub-step 3: FastAPI app (/health, /vehicles)
**Date:** 2026-06-25
**Phase:** Phase 1 (first ingestion)

### Concepts taught
- **HTTP request/response**: client sends method+path (+params), server returns status + JSON body.
- **REST**: tidy URL conventions around resources (`GET /vehicles`, `GET /health`).
- **FastAPI** (`@app.get(...)` turns a function into an endpoint) + **uvicorn** (the server).
- **Connection pool** (`psycopg_pool`): reuse a few ready DB connections instead of opening one
  per request. Opened once via FastAPI `lifespan`.
- **`DISTINCT ON (vehicle_id) ... ORDER BY vehicle_id, recorded_at DESC`** = latest row per vehicle.
- **Parameterized queries** (`route_id = %s`) prevent SQL injection.

### What we did
- Installed `psycopg-pool==3.3.1` (added to requirements). Created `backend/app/main.py`:
  lifespan-managed AsyncConnectionPool, `GET /health` (SELECT 1), `GET /vehicles?route=&limit=`.
- **Bug (Windows, round 2):** the first fix (`set_event_loop_policy` before `uvicorn.run`) FAILED —
  uvicorn installs its own ProactorEventLoop on Windows, overriding the policy, so the pool still
  errored (`PoolTimeout` after repeated "cannot use ProactorEventLoop"). **Robust fix:** on win32,
  build a `SelectorEventLoop(SelectSelector())` ourselves, `set_event_loop`, and run
  `uvicorn.Server(Config(app, loop="none"))` so uvicorn doesn't replace the loop. Linux/Docker path
  unchanged (`uvicorn.run`). Also dropped the deprecated policy call.
- Verified: `/health` → ok; `/vehicles?route=Red&limit=5` → 5 Red Line trains w/ Boston coords;
  `/vehicles` → 525 distinct vehicles. Committed `f173baa`.

### How to verify
- `.venv\Scripts\python.exe -m backend.app.main` then browse `http://localhost:8000/docs`, or
  `Invoke-RestMethod http://localhost:8000/vehicles?route=Red`.

### Gotcha reinforced
- **Windows + uvicorn + psycopg async**: must own the SelectorEventLoop and set uvicorn `loop="none"`.
  Setting the asyncio policy alone is NOT enough (uvicorn overrides it).

### Next step
**Phase 1, Sub-step 4 (final):** containerize the poller + API as compose services (Dockerfile +
`.dockerignore`; `api` and `poller` services that build from it, `depends_on` postgres healthy,
with in-container DATABASE_URL pointing at host `postgres` not `localhost`). Then Phase 1 Concept
Check.

---

## Entry 9 — Phase 1, Sub-step 4: containerized; PHASE 1 COMPLETE
**Date:** 2026-06-25
**Phase:** Phase 1 (first ingestion)

### Concepts taught
- **Dockerfile**: recipe to build our OWN image (FROM python:3.12-slim, install deps, copy code,
  CMD). Layer caching: copy requirements before code so deps don't reinstall on code changes.
- **.dockerignore**: keep junk/secrets (.venv, data/, .git, .env, frontend/) out of the build.
- **Service-name networking** (key gotcha): inside compose, containers reach each other by service
  name — DB host is `postgres`, NOT `localhost` (localhost in a container = that container).
- **depends_on: condition: service_healthy**: api/poller wait for Postgres to pass its healthcheck.

### What we did
- `Dockerfile` (python:3.12-slim — independent of host's 3.14; guaranteed wheels).
- `.dockerignore`.
- Added `api` + `poller` services to `docker-compose.yml`, each `build: .`, with DATABASE_URL/
  REDIS_URL overridden to use service-name hosts; api publishes `8000:8000`; both depend on
  postgres healthy.
- `docker compose build` then `docker compose up -d` → full stack (db+redis+api+poller).
- Verified: all 4 up; poller logs "stored ~515 positions" every ~10s; `/health` ok;
  `/vehicles?route=Orange` → 3 trains; DB newest row ~5s old (container poller actively writing).
  Committed `7cee8be`.

### How to verify
- `docker compose up -d` then `docker compose ps` (4 services), `docker compose logs poller -f`,
  `Invoke-RestMethod http://localhost:8000/vehicles?route=Red`.
- Stop with `docker compose down` (keeps data) — note: the poller keeps ingesting while up, so the
  table grows (bounded later in Phase 5 via Timescale retention).

### Phase 1 status: ✅ COMPLETE (pending Concept Check).
Known/deferred: duplicate rows each tick (no dedup) → Phase 2; no spatial index → Phase 2; no
Timescale/retention → Phase 5. The stack is currently UP and ingesting.

### Next step
Phase 1 **Concept Check** (why poller separate from API; what protobuf is & why the feed uses it;
what `GET /vehicles` does request→response). Then **Phase 2** (Redis Stream + processor, dedup/
idempotency, H3 tagging, GiST index + measured speedup, spatial endpoints, caching).

---

## Entry 10 — Phase 2, Sub-step 2a: Redis Stream pipeline + idempotency
**Date:** 2026-06-26
**Phase:** Phase 2 (streaming pipeline)

### Phase 1 Concept Check — PASSED
User: (1) poller normalizes load (1 fetch/10s regardless of users) ✓; (2) protobuf binary/fast/
needs library ✓ (sharpened: general-purpose format); (3) request→response — corrected a mix-up:
the **poller is NOT in the request path**; API reads the table (pool + DISTINCT ON latest per
vehicle + route filter) → JSON. Locked in: "poller writes in background, API reads on demand".

### Concepts taught
- **Redis Stream** = append-only log / conveyor belt. Producer `XADD`, consumer `XREADGROUP`.
- **Consumer group** + `XACK` = reliable sharing; **at-least-once delivery** (an item may arrive
  more than once).
- **Idempotency**: processing twice = no extra effect. Dedupe key `(vehicle_id, recorded_at)` via
  UNIQUE index + `INSERT ... ON CONFLICT DO NOTHING`. Analogy: re-scanning a used ticket.

### What we did
- Migration `0003_dedupe.sql`: TRUNCATE + UNIQUE index `(vehicle_id, recorded_at) NULLS NOT
  DISTINCT`.
- `backend/app/core/asyncrun.py`: shared `run()` (Windows SelectorEventLoop) for both workers.
- Refactored `poller.py`: decode -> `XADD` each vehicle to `vehicles:stream` (pipelined; maxlen
  200k). No DB access.
- New `processor.py`: `xgroup_create` (mkstream), loop `xreadgroup` (count 500, block 5s),
  `executemany` INSERT ... ON CONFLICT DO NOTHING (geom via ST_MakePoint), commit, then `XACK`.
- Added `redis==6.4.0` dep; added `processor` compose service; poller env trimmed to Redis-only.
- **Bug (caught & fixed):** removing DATABASE_URL from poller env crashed it — `config.py` did
  `os.environ["DATABASE_URL"]` at import. Made it `os.environ.get(...)` (optional) so a process
  that doesn't need the DB can still import config.
- Verified: poller "published ~760"; processor "processed 500/259"; `XPENDING` 0;
  **duplicates = 0** (total_rows == distinct_keys) while poller keeps republishing → idempotency
  proven. Committed `b246f81`.

### How to verify
- `docker compose logs processor -f`; `docker compose exec redis redis-cli XLEN vehicles:stream`;
  `... XPENDING vehicles:stream writers`; and the SQL dup check (duplicates column = 0).

### Next step
**Phase 2, Sub-step 2b:** H3 hexagon tagging. Add `h3_cell` column + the `h3` lib; processor
computes the H3 cell per position. Teach H3 (hexagonal global grid, resolutions). Then 2c (GiST
index + EXPLAIN ANALYZE speedup), 2d (spatial endpoints + caching).

---

## Entry 11 — Phase 2, Sub-step 2b: H3 hexagon tagging
**Date:** 2026-06-26
**Phase:** Phase 2 (streaming pipeline)

### Concept taught
- **H3**: Uber's hexagonal global grid; lat/lon -> stable hex id. Hexagons = equidistant
  neighbors, uniform area, hierarchical. Lets "near me" be an equality match on the cell (no
  geometry math). Resolution trade-off; chose **res 8** (~0.74 km² ≈ neighborhood).

### What we did
- Installed `h3==4.5.0` (v4 API: `h3.latlng_to_cell(lat, lon, res)` -> hex string).
- Migration `0004_h3.sql`: `ALTER TABLE vehicle_positions ADD COLUMN h3_cell TEXT`.
- Config `H3_RESOLUTION=8`. Processor computes + stores `h3_cell` per row (extra INSERT param).
- Verified: new rows tagged; top-neighborhoods works as pure `GROUP BY h3_cell` (busiest hex 23
  vehicles). Coverage: ~1k new rows tagged; ~25.7k older 2a rows remain NULL (historical, not
  backfilled — would need Python; not worth it). Committed `3e47c46`.

### Next step
**Phase 2, Sub-step 2c:** GiST spatial index + measured speedup. Teach indexes (seq scan vs index
scan, GiST/R-tree). Measure a "within 500 m" query with `EXPLAIN ANALYZE` BEFORE, add GiST index
on geom + B-tree on h3_cell (migration 0005), measure AFTER, record the plan change + timing for
METRICS/résumé. Then 2d (spatial endpoints + caching).

---

## Entry 12 — Phase 2, Sub-step 2c: GiST index + measured speedup
**Date:** 2026-06-26
**Phase:** Phase 2 (streaming pipeline)

### Concept taught
- **Index** = side structure to skip scanning every row (textbook back-index analogy). **Seq Scan**
  (check every row) vs **Index Scan** (jump to candidates). **GiST/R-tree** for geometry (bounding
  boxes skip whole regions); **B-tree** for h3_cell equality.
- **EXPLAIN ANALYZE** = show the query plan + actual timing.

### What we did (measured)
- BEFORE (no index): `ST_DWithin(geom, point, 0.006)` over ~40,336 rows → **Seq Scan**, ~89 ms warm
  (203 ms cold), 825 matches.
- Migration `0005_indexes.sql`: GiST on `geom` + B-tree on `h3_cell`.
- AFTER: same query → **Bitmap Index Scan** on `vehicle_positions_geom_gist`, **~1.4 ms** warm
  (~1.9 ms cold). **≈ 60× faster**; gap widens as table grows.
- Bonus: `WHERE h3_cell = ...` → Index Only Scan, ~0.24 ms.
- Recorded in **METRICS.md**. Committed `18d2133`.
- Note on index-usability: used degree-based `ST_DWithin(geom, point, 0.006°)` (≈500 m at Boston
  lat) so the GEOMETRY GiST index is usable; the `::geography` meters form cannot use it.

### Next step
**Phase 2, Sub-step 2d (final):** spatial API endpoints + caching. Add `GET /vehicles/near`
(ST_DWithin) and `GET /vehicles/cell/{h3}`; add short-TTL Redis caching to a hot endpoint. Teach
caching/TTL/staleness. Then Phase 2 Concept Check.

---

## Entry 13 — Phase 2, Sub-step 2d: spatial endpoints + caching; PHASE 2 COMPLETE
**Date:** 2026-06-26
**Phase:** Phase 2 (streaming pipeline)

### Concept taught
- **Cache + TTL**: store expensive results; serve repeats from memory. TTL = expiry = the
  staleness dial. For live data, a few seconds absorbs bursts without showing stale positions.

### What we did
- `main.py`: added a Redis client (in lifespan) + `cached_json(key, ttl, compute)` helper.
- `GET /vehicles/near?lat&lon&radius_m=500`: `ST_DWithin(geom, point, radius_m/111320°)` (uses the
  geometry GiST index; metres→degrees approx noted) + `recorded_at >= now() - 90s` recency filter +
  DISTINCT ON latest. **Cached 5s**.
- `GET /vehicles/cell/{h3}`: `WHERE h3_cell = %s` (B-tree) + recency + DISTINCT ON.
- Verified: near downtown → 21 vehicles; Redis key TTL=5 (caching proven); 2nd call same;
  `/vehicles/cell/882a307519fffff` → 1. Committed `13d7dd8`.

### Phase 2 status: ✅ COMPLETE (pending Concept Check).
Pipeline: poller → Redis Stream → processor (idempotent, H3-tagged) → PostGIS (GiST + h3 indexes) →
API (/vehicles, /vehicles/near cached, /vehicles/cell). Stack runs via `docker compose up` (5
services: postgres, redis, api, poller, processor).

### Next step
Phase 2 **Concept Check** (stream vs direct writes; idempotency + dedupe key; GiST + EXPLAIN
ANALYZE result; why hexagons). Then **Phase 3** (WebSockets + live map with fan-out).

---

## Entry 14 — Phase 3, Sub-step 3a: WebSocket + broadcaster (fan-out)
**Date:** 2026-06-26
**Phase:** Phase 3 (real-time frontend)

### Phase 2 Concept Check — PASSED
Stream=decoupling(+backpressure/resilience) ✓; idempotency corrected: dedupe key is the PAIR
`(vehicle_id, recorded_at)` — we KEEP history (many rows/vehicle), only drop the exact same
vehicle+timestamp repeat; "processing twice = no extra effect" ✓; GiST Seq Scan ~89ms → Index
Scan ~1.4ms ✓; hexagons = equality match on cell vs geometry math ✓.

### Concept taught
- **WebSocket vs HTTP**: WS is a persistent 2-way connection; the server PUSHES (dot moves on its
  own) vs HTTP's one-question-one-answer. **Fan-out**: one upstream read pushed to all clients.

### What we did
- `main.py`: `clients: set[WebSocket]`; `WS /ws/vehicles` (accept, add, prune on disconnect);
  `broadcaster()` background task (started in lifespan) — every 2s does ONE `LIVE_SQL` read
  (latest recent position per vehicle) and pushes to all clients (prunes dead ones).
- Verified programmatically: installed `websockets` (dev), test client connected and received a
  `positions` broadcast of **759 vehicles** within ~2s. Committed `29ec309`.

### Next step
**Phase 3, Sub-step 3b:** the MapLibre frontend page (live dots over a basemap via the WebSocket),
served at `/web`. Teach MapLibre basics. Visual verification: dots move; two browser tabs both
update from the same single feed (fan-out). Then Phase 3 Concept Check.

---

## Entry 15 — Phase 3, Sub-step 3b: live MapLibre map; PHASE 3 COMPLETE
**Date:** 2026-06-26
**Phase:** Phase 3 (real-time frontend)

### Concept taught
- **MapLibre**: style (free demotiles basemap, no key) + source (GeoJSON `vehicles`) + layer
  (circles). On each WS message, `getSource('vehicles').setData(...)` -> dots move.

### What we did
- `frontend/index.html`: MapLibre from CDN, Boston center, circle layer colored by subway line
  (Red/Orange/Blue/Green) else grey, click popup (route + vehicle id), status overlay, WS client
  with auto-reconnect.
- `main.py`: `app.mount("/web", StaticFiles(directory="frontend", html=True))` — served same-origin
  so the WS has no CORS issue.
- `docker-compose.yml`: api gets `./frontend:/app/frontend:ro` volume (edit HTML w/o rebuild).
- **Gotcha:** `Invoke-WebRequest` needs `-UseBasicParsing` in this non-interactive PS shell.
- Verified: `GET /web/` 200; **user confirmed in browser** — dots over Boston move every ~2s,
  click popup shows route (e.g. "86") + vehicle (y1939), and TWO tabs update together (fan-out).
  Committed `18cbdda`.

### Phase 3 status: ✅ COMPLETE (pending Concept Check).
Live map at http://localhost:8000/web/. (Minimal map; Phase C builds the Next.js+CopilotKit
version. Phase 4 adds the real route/stop network as vector tiles under the dots.)

### Next step
Phase 3 **Concept Check** (WS vs HTTP; fan-out & why it scales; path from "new position processed"
to "dot moves"). Then **Phase 4** (vector tiles: Martin/pg_tileserv serving routes+stops from
PostGIS, rendered under the live dots).

---

## Entry 16 — Phase 4, Sub-step 4a: Martin tile server + route_shapes view
**Date:** 2026-06-26
**Phase:** Phase 4 (vector tiles)

### Phase 3 Concept Check — PASSED
WS=persistent push vs HTTP one-shot ✓; fan-out scales because upstream work (1 poll + 1 DB read/2s)
stays constant as viewers grow — only cheap per-socket sends increase ✓; path: poller→stream→
processor→DB, then broadcaster (every 2s) 1 read→WS push→browser setData→MapLibre redraws ✓.
Write side and push side decoupled, meet only at the DB.

### Concept taught
- **Vector tiles / MVT**: world sliced into z/x/y squares; browser fetches only on-screen tiles;
  MVT = compact protobuf geometry (data, not images → styled live, crisp at any zoom).
- **Tile server (Martin)**: generates MVT from PostGIS per requested tile (clips + reprojects
  4326→3857 automatically).

### What we did
- Migration `0006_route_shapes.sql`: VIEW joining shapes→trips→routes, exposing geom +
  `'#'||route_color` (grey fallback). 1,150 colored shapes.
- Added `tiles` (Martin, `ghcr.io/maplibre/martin`) compose service on :3000, DATABASE_URL at
  host `postgres`. Auto-discovers tables/views with geometry.
- Verified: `/catalog` lists `route_shapes` + `stops`; tiles `route_shapes/11/619/757` (287 KB) and
  `stops/11/619/757` (344 KB) return 200 MVT. (Tiles hefty at z11 → show stops only at higher zoom
  in 4b.) Committed `5c4c18e`.

### Next step
**Phase 4, Sub-step 4b:** add tile layers to the map (route lines colored by route_color under the
dots; stops as circles, zoom-gated) + stop click popup. Visual verification. Then Phase 4 Concept
Check.

---

## Entry 17 — Phase 4, Sub-step 4b: render network tiles; PHASE 4 COMPLETE
**Date:** 2026-06-26
**Phase:** Phase 4 (vector tiles)

### What we did
- Verified Martin CORS: with an `Origin` header it returns `access-control-allow-origin:
  http://localhost:8000` — works out of the box (no config). (Plain request omits Origin → no ACAO,
  which is normal.)
- `frontend/index.html`: added vector source `routes` (`/route_shapes`) as a `line` layer colored
  by `['get','route_color']`; vector source `stops` as a `circle` layer with `minzoom: 13`
  (zoom-gated) + stop click popup (stop_name). Vehicles layer added LAST so dots stay on top.
- Served via the existing `./frontend` volume (no rebuild).
- **User verified in browser:** colored route lines under the dots; stops appear when zoomed in;
  stop popups work.
- **Q&A:** user noticed the Blue Line crossing water — confirmed REAL (harbor tunnel + coastal
  route to Revere); not a coord bug (a lon/lat swap would put ALL lines in the ocean). Basemap is
  coarse demotiles. Committed `b22ca3b`.

### Phase 4 status: ✅ COMPLETE (pending Concept Check).
Map now shows the real MBTA network (routes + stops as vector tiles from Martin) under live
WebSocket dots. Services: postgres, redis, api, poller, processor, tiles.

### Next step
Phase 4 **Concept Check** (why not send whole-city geometry; what a vector tile is + what the tile
server does; 4326 vs 3857). Then **Phase 5** (TimescaleDB hypertable + retention + R2 offload +
continuous aggregate + derive arrival labels for ML).

---

## Entry 18 — Phase 4 Concept Check + Phase 5a: TimescaleDB hypertable
**Date:** 2026-06-26
**Phase:** Phase 4 → 5 boundary

### Phase 4 Concept Check — PASSED
Tiles: whole-city geometry too slow/big; tiles = z/x/y boxes, browser fetches only visible ✓.
Tile server corrected: Martin QUERIES PostGIS for geometry in a tile, CLIPS it, ENCODES MVT,
returns bytes — generated on demand (not pre-rendered); port/CORS are just plumbing. 4326=GPS
(our DB), 3857=web tiles, Martin reprojects ✓.

### Concept taught (Phase 5)
- **Time-series + hypertable**: TimescaleDB auto-partitions a table by time into chunks ("page per
  day"). Time-scoped queries/cleanup touch only relevant chunks; unlocks retention + continuous
  aggregates. Hypertable rules: time column NOT NULL; unique indexes must include it.

### What we did (5a)
- **DB image switch**: `postgis/postgis:16-3.4` → `timescale/timescaledb-ha:pg17` (bundles
  TimescaleDB + PostGIS + pgvector). New PGDATA path `/home/postgres/pgdata/data`. Destructive:
  `docker compose down -v` wiped volumes (lost throwaway history; static GTFS reloaded).
- Migration `0001` now explicitly `CREATE EXTENSION IF NOT EXISTS postgis` (HA image doesn't
  auto-create it). New `0007_timescale.sql`: recorded_at NOT NULL, drop surrogate id PK,
  `create_hypertable('vehicle_positions','recorded_at')`.
- Processor: `recorded_at` falls back to ingestion time when feed omits ts (NOT NULL).
- Re-ran migrations 0001–0007; reloaded GTFS (403/10308/121935/3.34M/1150); rebuilt + up all 6
  services. Verified: hypertable present (1 dim), data flowing (1156 rows, 1 chunk), API healthy.
  Committed `c92776d`.

### Next step
**Phase 5, Sub-step 5b:** retention policy (auto-drop raw rows older than ~72h) + a continuous
aggregate (per-route hourly travel-time rollup). Teach retention + continuous aggregates. Then 5c
(arrival labels + Parquet offload).

---

## Entry 19 — Phase 5, Sub-steps 5b–5c: retention, aggregate, arrival labels; PHASE 5 COMPLETE
**Date:** 2026-06-26
**Phase:** Phase 5 (time-series & history)

### Concepts taught
- **Retention policy**: background job dropping whole time-chunks older than a cutoff (near-instant
  vs row deletes); bounds storage.
- **Continuous aggregate**: incrementally-maintained materialized view of rollups; survives
  retention (keep rollups, drop raw). (No count(DISTINCT) allowed inside.)
- **Arrival labels**: detect arrival by NEAREST APPROACH (closest position within 75 m of a stop);
  delay = actual arrived_at − scheduled_ts (GTFS local arrival_time placed on the service date in
  America/New_York, made absolute).

### What we did
- **5b**: Migration `0008` — `add_retention_policy('vehicle_positions', 72h)` + continuous
  aggregate `route_activity_hourly` (per-route hourly position_reports + avg_bearing) with a
  refresh policy. Verified jobs registered; manual refresh shows data (route 66 = 318/hr).
  Committed `2509205`.
- **5c**: Migration `0009` — `vehicle_arrivals` table. `db/derive_arrivals.sql` — upsert via
  DISTINCT ON (trip,stop) closest approach within 75 m, ON CONFLICT DO NOTHING. Ran it: **4,371
  arrivals**, avg dist 22 m, realistic delays (early/late, avg ~242 s). Committed `a548f7b`.
- **Deferred**: R2 Parquet offload → Phase J (needs Cloudflare creds; retention already bounds
  local storage). Noted, not skipped.

### Phase 5 status: ✅ COMPLETE (pending Concept Check).
vehicle_positions = hypertable w/ 72h retention; route_activity_hourly continuous aggregate;
vehicle_arrivals = ML labels (re-run db/derive_arrivals.sql periodically as history grows).

### Next step
Phase 5 **Concept Check** (hypertable + why partition by time; retention + where offload goes;
positions→arrival labels). Then **Phase 6** (LightGBM ETA predictor: features → baselines → train
time-split → MAE vs baseline → serve via GET /stops/{id}/arrivals).

---

## Entry 20 — Phase 5 Concept Check + autonomous data collection (COLLECTING)
**Date:** 2026-06-26
**Phase:** Phase 5 → 6 boundary (data-collection pause)

### Phase 5 Concept Check — PASSED
Hypertable=time-chunked table; corrected the WHY: partition by time because queries/cleanups are
time-scoped → DB skips irrelevant chunks (not "snapshots") ✓. Retention drops >72h (near-instant =
drops whole chunks); continuous aggregate keeps rollups as raw is deleted ✓. Arrival = within ~75 m
nearest approach, delay = actual vs scheduled stop_times ✓.

### Decision: COLLECT FIRST (then build Phase 6)
User chose to accumulate richer history before training. Set up **autonomous collection**:
- Migration `0010_arrival_job.sql`: added `service_date` to `vehicle_arrivals` (multi-day safe;
  PK now (trip_id, stop_id, service_date)); moved derivation into a `derive_arrivals()` PROCEDURE;
  registered a **TimescaleDB scheduled job running every 10 min**. `db/derive_arrivals.sql` now
  just `CALL derive_arrivals();`.
- Verified: job registered (10-min interval); manual CALL grew arrivals 4,371 → 7,869.
- Committed `8a1fa80`.

### >>> CURRENT STATE: stack left RUNNING to collect data <<<
- `docker compose` stack up (postgres+redis+api+poller+processor+tiles). Positions ingest
  continuously; arrivals auto-derive every 10 min; 72h retention bounds storage.
- Laptop + Docker must stay running to collect. (restart:unless-stopped resumes after a Docker
  restart.) To pause: `docker compose stop poller processor`. To check progress:
  `docker compose exec -T postgres psql -U livetransit -d livetransit -c "SELECT count(*),
  count(DISTINCT service_date) FROM vehicle_arrivals;"`
- **RESUME POINT:** when user returns, START **Phase 6** (LightGBM ETA predictor): features →
  baselines (schedule + historical avg) → time-split train → MAE vs baseline → serve
  `GET /stops/{id}/arrivals` → frontend accuracy panel.

---

## Entry 21 — Phase 6, Sub-steps 6a–6b: features + trained model (MAE 44s)
**Date:** 2026-06-26
**Phase:** Phase 6 (ML core)

### Data check before starting
~37k arrivals over ~7h (evening+overnight, 162 routes). ~7% outlier labels (|delay|>1h from
late-night/timezone edge cases). User chose START NOW; outliers filtered in the feature step.

### Concept / design
- **Framing**: delay-propagation regression — predict delay at an upcoming stop from current
  (upstream) delay + hour/dow/route/stop_sequence. `eta = scheduled + predicted_delay`.
- **Leakage guard**: features only from the prior stop; **time-based split** (earlier 80% train,
  later 20% test), never random.
- ML deps installed in venv on Python 3.14 (lightgbm 4.6.0, pandas 3.0.3, sklearn 1.9.0) — wheels
  exist, no container needed. Pinned in `backend/requirements-ml.txt`.

### What we did
- `backend/app/ml/features.py`: SQL self-join on vehicle_arrivals -> (current_delay, hour, dow,
  stop_sequence, route_id) + target_delay; filters |delay|<=1800s & dist_m<60. **30,784 clean
  rows**, corr(current_delay,target_delay)=**0.952**.
- `backend/app/ml/train.py`: time-split; baselines + LightGBM; saves model+meta to `models/`
  (git-ignored). Held-out MAE (s): schedule 249.3, hist-avg 203.7, persistence 48.7, **MODEL 44.0**
  → 82.3% better than schedule, 9.6% better than persistence. Recorded in METRICS.md.
- Commits `f781ac8` (features), `77cb0d2` (train+metrics). Model file NOT committed (git-ignored).

### Next step
**Phase 6, Sub-step 6c:** serve predictions. `predictor.py` (load model via lightgbm Booster +
numpy, no pandas) + `GET /stops/{id}/arrivals` (upcoming arrivals for running trips → predicted
ETA). Mount `./models` into the api container; add lightgbm to API image. Frontend: stop click →
predicted-arrivals panel + accuracy (MAE vs baseline). Then Phase 6 Concept Check.

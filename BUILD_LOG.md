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

---

## Entry 22 — Phase 6, Sub-step 6c: serve predictions + UI panel; PHASE 6 COMPLETE
**Date:** 2026-06-26
**Phase:** Phase 6 (ML core)

### What we did
- `backend/app/ml/predictor.py`: load model via `lgb.Booster` + numpy (no pandas → lean API
  image); `predict_delays(rows)`; exposes meta (MAE stats).
- `main.py`: load model in lifespan (graceful if absent); `GET /stops/{id}/arrivals` — active trips
  today ⋈ stop_times for the stop, not yet reached, **|current_delay|<=1800 filter** (drops corrupt
  after-midnight delays), predict → ETA = scheduled + predicted_delay; returns accuracy block.
- `Dockerfile`: **+libgomp1** (LightGBM OpenMP runtime; missing on slim → was the startup crash).
- compose: mount `./models:/app/models:ro`. `lightgbm` added to API requirements.
- `frontend/index.html`: stop click → side panel with predicted arrivals (time + early/late tag,
  Boston tz) + footer "MAE 44s vs schedule 249s".
- **Bugs fixed:** (1) libgomp1 missing → API crash. (2) serving fed raw outlier current_delay
  (~-24h after-midnight) → garbage preds; added |delay|<=1800 serving filter.
- Verified: endpoint returns sensible preds (route 28: current -871s → pred -566s); user confirmed
  the UI panel + accuracy footer render. Commits `a3c8021` (backend), `314eae5` (frontend).

### >>> REMINDER (saved to memory `retrain-eta-model-full-day`) <<<
Model v1 trained on evening+overnight ONLY. **On/after 2026-06-27**, once full-day data (incl.
morning rush) is collected, RETRAIN: `python -m backend.app.ml.train` + `docker compose restart
api`, then do an MAE split-by-hour eval. User asked to be reminded next session.

### Phase 6 status: ✅ COMPLETE (pipeline; v1 model). Stack still RUNNING to collect full-day data.

### Next step
Phase 6 **Concept Check**, then continue building (Phase 7 observability, or 8/9) while data
collects. Retrain tomorrow.

---

## Entry 23 — Phase 6 Concept Check + Phase 7a: Prometheus metrics
**Date:** 2026-06-26
**Phase:** Phase 6 → 7

### Phase 6 Concept Check — PASSED
Regression (continuous delay) ✓; time-split because delays are autocorrelated → random split leaks
near-in-time samples into both sets ✓; leakage avoided in BOTH features (only past-knowable) AND
split (time-based) — user had split, added feature half ✓; baselines needed to interpret 44s,
persistence was the hard one (corr 0.95) ✓.

### Concept taught (Phase 7)
- Logs (events, text) vs metrics (numbers over time). Prometheus SCRAPES /metrics; Grafana draws
  dashboards. Counter (up-only) / Gauge (up-down) / Histogram (distribution → p50/p99).

### What we did (7a)
- `backend/app/core/metrics.py`: shared Counter/Gauge/Histogram defs (+ worker metrics ports).
- Poller: `start_http_server(9101)`; POLLS, POSITIONS_PUBLISHED, POLL_FAILURES, FEED_TS (newest
  vehicle ts → freshness).
- Processor: `start_http_server(9102)`; MESSAGES, BATCHES.
- API: `/metrics` route (generate_latest), latency middleware labeled by ROUTE TEMPLATE (low
  cardinality — avoids the stop-id explosion), WS_CLIENTS gauge.
- `prometheus-client==0.24.1` dep; `ops/prometheus.yml` (scrape api:8000, poller:9101,
  processor:9102 @10s); `prometheus` compose service on :9090.
- Verified: all 3 targets UP; positions_published=137=messages (balanced); ws_clients=1;
  feed_age≈21s. Committed `024ccc6`.
- Note: shared metrics module → every process exposes all metric names (0 for ones it doesn't
  use); filter by `job` in Grafana.

### Next step
**Phase 7, Sub-step 7b:** Grafana (provisioned datasource + dashboard) on :3001 (3000 is Martin);
panels for ingestion rate, feed age, WS clients, API p50/p99, poll failures. Screenshot for README.
Then Phase 7 Concept Check.

---

## Entry 24 — Phase 7, Sub-step 7b + alerts: Grafana dashboard; PHASE 7 COMPLETE
**Date:** 2026-06-26
**Phase:** Phase 7 (observability)

### What we did
- **Grafana** provisioned-as-code: `ops/grafana/provisioning/datasources/datasource.yml`
  (Prometheus, uid=prometheus), `.../dashboards/provider.yml`, and
  `ops/grafana/dashboards/livetransit.json` (6 panels: ingestion events/sec, feed age stat w/
  thresholds, WS clients, API p50/p99 via histogram_quantile, poll failures, positions total).
- compose `grafana` service on **:3001** (3000=Martin), anonymous Viewer enabled (no login).
- **Alerts**: `ops/alerts.yml` — `FeedStale` (feed >60s) + `ProcessorStalled` (publishing but not
  consuming 2m); `rule_files` in prometheus.yml; mounted. Both load **inactive** (healthy).
- Verified via API: datasource + dashboard provisioned; **user confirmed** dashboard loads with
  live data, feed age green, ingestion lines moving. Commits `46239c3`, `c35fd79`.
- TODO (Part 6 polish): screenshot the dashboard for the README (user action).

### Phase 7 status: ✅ COMPLETE (pending Concept Check).
Observability: /metrics on all services → Prometheus (:9090, scrape 10s, 2 alert rules) → Grafana
(:3001 dashboard). Stack now 8 services.

### Next step
Phase 7 **Concept Check** (logs vs metrics; counter/gauge/histogram; p99 & why over average).
Then continue — likely **Phase 8** (pytest: dedupe/idempotency, arrival detection, feature build,
API contract) and/or **Phase 9** (CI/CD), while data collects for tomorrow's retrain.

---

## Entry 25 — Phase 7 Concept Check + Phase 8: tests; PHASE 8 COMPLETE
**Date:** 2026-06-26
**Phase:** Phase 7 → 8

### Phase 7 Concept Check — PASSED
Logs=text events vs metrics=numbers over time for live analysis ✓; counter up-only / gauge up-down
✓; histogram corrected (= distribution via buckets → percentiles, not "a plot"); **taught p50/p99**
(user didn't know): p99 = 99% faster than this = the slow tail; care over average because averages
hide bad outliers that real users feel.

### Concept taught (Phase 8)
- Test the logic that would silently corrupt data/mislead: idempotency, feature/label correctness,
  API contract. Not trivial getters. Unit (fast, pure) vs integration (real test DB).

### What we did
- `pytest==9.1.1` (+ `backend/requirements-dev.txt`), `pytest.ini` (testpaths=backend/tests).
- **Unit** `test_ingest.py`: `parse_feed` (synthetic protobuf: keeps only vehicles w/ position,
  skips alerts) + `to_row` (lon,lat order; ts→datetime; bearing/empty→None; recorded_at fallback).
  Caught float32: protobuf lat/lon → use `pytest.approx`.
- **Integration** `conftest.py` (disposable `livetransit_test` DB, sync psycopg, skips if no PG) +
  `test_integration.py`: idempotent INSERT (dup key → 1 row), history kept + latest-per-vehicle,
  geom (lon,lat) in Boston. Exercises the REAL `INSERT_SQL`.
- Also installed prometheus-client into the venv (poller import needs it for tests).
- **6 passed.** Committed `722ba4d`.

### Phase 8 status: ✅ COMPLETE (pending Concept Check). Run: `.venv\Scripts\python.exe -m pytest`.

### Next step
Phase 8 **Concept Check** (unit vs integration vs e2e; what's most worth testing here; why fixtures
over live feed). Then **Phase 9** (GitHub Actions CI: lint + pytest w/ Postgres service container +
build image). Retrain model tomorrow w/ full-day data (see memory).

---

## Entry 26 — Phase 8 Concept Check + Phase 9: CI green; BODY (0–9) COMPLETE
**Date:** 2026-06-26
**Phase:** Phase 8 → 9

### Phase 8 Concept Check — PASSED
Corrected unit/integration framing: it's ISOLATION (unit=isolated logic no deps; integration=real
components together e.g. real Postgres; e2e=whole flow), not "row vs table"; got 3+3 split right.
What-to-test ✓. Fixtures: added the determinism/no-network reason for the synthetic feed.

### Concept taught (Phase 9)
- CI (run checks on every push) / CD (auto-deploy on pass). GitHub Actions = workflows/jobs/steps.
  **Service container** = a real Postgres spun up inside the workflow for integration tests.

### What we did
- `ruff` linter + `ruff.toml` (E,F,I,W; line-length 100). Fixed 2 E501s. `ruff==0.15.20` pinned in
  requirements-dev.
- `.github/workflows/ci.yml`: `test` job (postgis service container, DATABASE_URL env, install
  reqs, ruff check, pytest) + `build` job (docker build).
- **Bug (green locally / red in CI):** CI runs bare `pytest` which (unlike `python -m pytest`)
  doesn't put repo root on sys.path → `ModuleNotFoundError: backend`. Reproduced locally with bare
  pytest; fixed with `pythonpath = .` in pytest.ini.
- Verified via GitHub API polling: first run FAILED (test), build passed; after fix run **SUCCESS**.
  Commits `779c341`, `8acfec2`.
- Optional (user, in repo settings): enable branch protection so main requires green CI.

### >>> BODY COMPLETE: Phases 0–9 done. <<<
Live transit system: ingest→stream→process→PostGIS/Timescale→API/WS→map+tiles, ML ETA predictor,
observability (Prometheus/Grafana), tests, green CI. 8 docker services. Repo:
https://github.com/Chikap1009/livetransit-copilot

### Next step
Phase 9 **Concept Check** (CI vs CD; workflow stages; why CI needs its own DB service). Then the
**BRAIN** — **Phase A** (first Pydantic AI agent: 3 read-only tools + Gemini gateway + ReAct loop +
POST /agent/ask). NOTE: needs a Google AI Studio (Gemini) API key from the user. Also: retrain ETA
model tomorrow w/ full-day data (memory `retrain-eta-model-full-day`).

---

## Entry 27 — Phase 9 Concept Check + Phase A: first agent WORKS
**Date:** 2026-06-26
**Phase:** Phase 9 → A (BODY → BRAIN)

### Phase 9 Concept Check — PASSED
CI=auto checks on push (built it) / CD=auto deploy on green (Phase J) ✓; corrected: ruff & pytest
are separate steps (checkout→setup→install→ruff→pytest w/ PG service; build job=docker build);
corrected #3: CI needs its own DB because the runner has NONE + isolation + reproducibility (NOT
"scale/production").

### Concepts taught (Phase A)
- program vs chatbot vs agent; ReAct loop (reason→act→observe); tool/function calling (model
  REQUESTS, your code RUNS); Pydantic AI ("FastAPI for agents", one-string provider switch); hosted
  LLM + free tiers.

### What we did
- **Gemini key**: user pasted (format `AQ.Ab8...` — newer style, valid). Stored in git-ignored
  `.env` (GEMINI_API_KEY); placeholder in `.env.example`; passed to api container via compose
  `${GEMINI_API_KEY}`. Flagged: regenerate if worried (shared in chat).
- Installed `pydantic-ai-slim[google]==2.0.0`. **Gotcha:** v2 provider rename — `google-gla` →
  use **`google:gemini-2.5-flash`**. Smoke test → "pong".
- `agent/gateway.py` (MODEL + UsageLimits(request_limit=8)), `agent/tools.py`
  (get_vehicle_positions [DB], predict_eta [DB+LightGBM], get_service_alerts [live Alerts.pb]),
  `agent/copilot.py` (Agent + deps=pool + system prompt + 3 @copilot.tool), `POST /agent/ask`
  (returns answer + tools_used).
- Verified: "Red Line trains?" → get_vehicle_positions → "18 trains" + coords; "Orange alerts?" →
  get_service_alerts → 5 real alerts. Ruff clean. Committed `527e0ba`.

### Phase A status: ✅ COMPLETE (pending Concept Check).

### Next step
Phase A **Concept Check** (draw ReAct loop; what a tool is + function calling; question→answer
flow; why hosted LLM). Then **Phase B** (structured outputs + streaming reasoning). Retrain ETA
model tomorrow (memory).

---

## Entry 28 — Phase A Concept Check + Phase B: structured outputs + streaming; COMPLETE
**Date:** 2026-06-26
**Phase:** Phase A → B

### Phase A Concept Check — PASSED
ReAct loop ✓; tool=function, model decides+requests / your code runs (sharpened) ✓; flow w/ live
data entering at tool execution ✓; hosted = VRAM + server-reachable ✓.

### Concepts taught (Phase B)
- **Structured outputs**: model fills a Pydantic schema (not prose); validated; auto-retry on
  malformed → dependable, app-consumable data. **Streaming**: push tool-steps + answer live; the
  visible reasoning trace is the agentic "wow".

### What we did
- `agent/schemas.py`: `ArrivalAnswer` (stop + Arrival[route,eta,status] + summary) and `Answer`
  (summary+routes+facts). `copilot` `output_type=[ArrivalAnswer, Answer]` → model picks + validates.
- `POST /agent/ask` returns `{answer_type, answer (validated obj), tools_used}`. Learned: structured
  output is delivered via an internal `final_result_*` tool (filtered out).
- `GET /agent/stream` (SSE) via `copilot.iter()`: emits `tool` events live, then a `result` event
  with the structured answer. Minimal chat box added to the map page (EventSource).
- **Bugs:** (1) v2 provider name (prev entry); (2) E501 lint → used `isinstance(ToolCallPart)`;
  pushed lint-failing commit then fix — CI red then green (2527753).
- Verified: `/agent/ask` returns Answer vs ArrivalAnswer correctly; SSE streams tool events then
  result; **user confirmed** chat box streams steps + shows answer card. Commits `8cc7fd6`,
  `2527753`.

### Phase B status: ✅ COMPLETE (pending Concept Check).

### Next step
Phase B **Concept Check** (why structured outputs + malformed handling; what's streamed + why the
tool-step trace matters). Then **Phase C** (Next.js + CopilotKit + map fusion — agent draws on the
map). Retrain ETA model tomorrow (memory `retrain-eta-model-full-day`).

---

## Entry 29 — Phase C: Next.js + CopilotKit + map fusion (C1, C2 done; C3 mostly done)
**Date:** 2026-06-27
**Phase:** Phase C (real frontend)

### Phase B Concept Check — PASSED (structured outputs = fillable form, validated, auto-retry;
streamed tool steps = transparency/trust, avoids "frozen" feel).

### C1 — Next.js app + live map
- Scaffolded `web/` (Next.js **16**, App Router, TS). web/AGENTS.md warns Next is newer than
  training -> read `web/node_modules/next/dist/docs/...` first ('use client' + useEffect confirmed).
- `web/app/components/LiveMap.tsx` (MapLibre + WS dots + Martin tiles + status overlay + vehicle
  popup), `StopPanel.tsx` (polished React prediction panel). Dev: `npm --prefix web run dev --
  --port 3002`. API CORS enabled (`allow_origins=*`; tighten Phase J). Old `/web` kept as legacy.

### C2 — CopilotKit chat -> Python agent (AG-UI)
- Backend `POST /agent/ag-ui` via `pydantic_ai.ui.ag_ui.AGUIAdapter.dispatch_request(..., output_type
  =str)` (v2 moved AG-UI; read source to find it). Installed `pydantic-ai-slim[google,ag-ui,groq]`.
- Frontend: `@copilotkit/*` 1.61 + `@ag-ui/client`. `app/api/copilotkit/route.ts` (CopilotRuntime +
  HttpAgent -> :8000/agent/ag-ui + EmptyAdapter). `AppShell.tsx` (provider + CopilotSidebar).
  `CopilotActions.tsx` = catch-all `useCopilotAction({name:'*'})` -> clean tool-call pills.
- **Groq fallback (Phase H early)**: `FallbackModel(gemini, groq×4, fallback_on=_should_fallback)`.
  Gemini free tier ~20/window. Bugs fixed: (1) streaming raised raw google ClientError 429 (not
  ModelAPIError) -> fallback never fired; fixed with message-matching fallback_on. (2) Groq streaming
  tool-calls flaky (~2/3 "Failed to call a function") -> list Groq ×4 to retry. Chat (text path)
  works on Groq; structured /agent/ask weak on Groq (known).
- Bug: `predict_eta` returned STALE past arrivals -> `HAVING max(arrived_at)>=now()-30min` +
  `scheduled_ts>=now()-2min` (in tool + /stops endpoint).

### C3 — map fusion
- `LiveMap` `useCopilotAction` handlers (mapRef): **highlightRoute** (dim others + neon cyan + dark
  casing), **dropPin**, **clearMap**. System prompt says agent can draw. Highlight VERIFIED by user.
- REMAINING (C3 finale): trip planning "A->B + ETA". Plan: lightweight GTFS direct-trip `plan_trip`
  tool (match stop names -> direct route -> times/ETA -> draw segment). OTP = stretch (heavy).

### >>> DISK CRISIS (resolved) <<<
Docker crashed: C: hit 0.3 GB free (475 GB). ~20 rebuilds -> 30 GB unused images + 22 GB build cache.
`docker system prune -af` (NO --volumes; data safe) reclaimed 26 GB; C: -> 3.7 GB; api rebuilt.
GOING FORWARD: run `docker system prune -af` after heavy build sessions.

### >>> PAUSE POINT — stack RUNNING to collect data <<<
- 8 services up + Next.js dev :3002. Frontend: http://localhost:3002 (CopilotKit) / :8000/web (legacy).
- TODO on resume: (1) **Retrain ETA model** (`python -m backend.app.ml.train` + `docker compose
  restart api`; memory `retrain-eta-model-full-day`). (2) **Agent eval pass** (memory
  `agent-eval-pass`). (3) **C3 finale** lightweight `plan_trip`. (4) Then Phases D,E,F,G,H,I,J.
- Phase C commits (all pushed): 860bb42, 300c129, af61cd2, 67a306f, 3f02536, 9d1bd1e, 253b771,
  f53b53c, a4e8cd6, + fallback 0e03807/2fd4f69/2393901.

---

## Entry 30 — Phase C finale: trip planning with transfers + map fusion; PHASE C COMPLETE
**Date:** 2026-06-27
**Phase:** Phase C (real frontend) — C3 finale

### What the user asked for
The "A → B + ETA" trip planner, but explicitly: when A and B are NOT on one direct
route, don't just say "no direct route" — tell the user the **line changes and stop
changes** to reach B, with **per-leg ETA and a total ETA**, and draw it on the map.

### The new concept taught: minimum-transfers routing (BFS over the route graph)
- Model the network as **stations connected by routes**. Riding one route from any of its
  stations to another = **one leg**; switching routes at a shared station = **one transfer**.
- A **breadth-first search** (expand "reachable in 1 leg, then 2, …") finds the path with the
  **fewest transfers** first — what a rider usually wants. Then a scheduled-times lookup fills
  in the clock for each leg, chained so each leg departs after the previous arrives (+3 min
  transfer buffer) → total wall-clock ETA.
- Scope guard (kept lightweight, NOT OpenTripPlanner): **direct** trips work on ANY route
  (incl. buses); **transfer** routing runs only over the rapid-transit graph
  (`route_type IN (0,1,2)` = subway/light-rail/commuter-rail, ~22 routes) where "fewest
  changes" answers are genuinely correct. Bus-only pairs with no direct route are declined
  honestly rather than inventing bad multi-bus paths.

### What we did
- **Migration `0011_stop_times_stop_idx.sql`**: B-tree index on `stop_times(stop_id)`. The
  planner filters the 3.3M-row table by `stop_id` (only the `(trip_id, stop_sequence)` PK
  existed) → turns seq scans into index scans. (Phase 2 indexing lesson, B-tree flavor.)
- **`backend/app/agent/routing.py`** (new, the engine):
  - `_build_rail_graph` / `get_rail_graph` — station↔route adjacency + platforms + coords for
    the rail network; **cached module-level** (static schedule data; ~280 ms first call, then 0).
  - `_resolve_station` — name → best station, **rail-preferred + exact/prefix-preferred** (fixed
    a real bug: "Kendall"/"Harvard" first matched random *bus* stops like "Western Ave @ N
    Harvard St", hijacking the route; now SQL orders exact→prefix→short-name so the LIMIT can't
    drop the real station, and rail stations win ties).
  - `_find_leg` — soonest single trip boarding in stop-set A then alighting in stop-set B (after
    a ready-time), with GTFS `HH:MM:SS` (incl. >24h) → absolute NY-tz timestamps.
  - `_bfs` / `_reconstruct` — min-transfers path → `[(route, board_station, alight_station)]`.
  - `plan_trip` — resolve → try direct (any route) → else BFS over rail → fill+chain leg times.
    Returns `{found, origin, destination, transfers, total_minutes, departs, arrives, legs[],
    draw[]}` where each `draw` entry is **pre-shaped** for the frontend `drawTrip(legs)` action.
- **`tools.py`** + **`copilot.py`**: registered `@copilot.tool plan_trip`; system prompt teaches
  the agent to call `plan_trip` then pass its `draw` array to `drawTrip`, narrate each leg + say
  where to change lines, and report `total_minutes` **verbatim** (don't recompute — it includes
  transfer waits).
- **`web/app/components/LiveMap.tsx`**: new `drawTrip(legs)` CopilotKit action (`object[]` param)
  — highlights **all** legs' routes (`['in', route_id, [..]]`), drops a green **Start** pin, amber
  **Transfer** pins (labeled "Transfer to <next line> at <stop>"), a red **Destination** pin, and
  `fitBounds` to frame the whole trip. Added a `TripLeg` type.

### Bugs caught & fixed during the build
1. `%-I` strftime (no-zero-pad) is **Linux-only** → crashed on Windows dev; made `_clock`
   portable (`%I…`.lstrip("0")).
2. Bus-stop name-hijack (above) → rail-preferred, exact/prefix-ordered resolution.
3. Sloppy total-minutes calc → now true wall-clock first-board→last-alight (only when every leg
   is timed).

### How it was verified
- **Engine** (direct test vs live DB): Kendall→Park St = direct Red 4m; Kendall→Boylston = Red→
  Green @ Park St (1 transfer); Harvard→Airport = Red→Green→Blue (2 transfers, times chained);
  Davis→Lechmere = Red→Green. 43–283 ms.
- **Agent**: `POST /agent/ask "Kendall to Boylston"` → `tools_used:["plan_trip"]`, correct
  narration. (Note: the `/agent/ask` *structured* path is still flaky on the Groq fallback —
  known since Entry 29; the user-facing CopilotKit chat uses the text path and `drawTrip`.)
- **Browser (user confirmed)**: all 4 scenarios (transfer, direct, two-transfer, clear) draw and
  narrate correctly at http://localhost:3002.
- ruff clean; `tsc --noEmit` clean; api rebuilt + healthy.

### Phase C status: ✅ COMPLETE.
Next.js + CopilotKit frontend; agent draws on the map (highlightRoute, dropPin, drawTrip,
clearMap); structured outputs + streaming; Groq fallback. The Bible's Phase C threshold —
"ask a trip question and watch the agent draw the route" — is met, with transfers.

### >>> Reminders still pending (deferred to AFTER all phases, per user) <<<
(1) Retrain ETA model w/ full-day data (memory `retrain-eta-model-full-day`). (2) Comprehensive
agent eval pass (memory `agent-eval-pass`). User chose to do both once all phases are done.

### Next step
**Phase D** — memory: conversation (Redis) + long-term/vector (pgvector) so the agent remembers
turns, the user's home/work stops, and preferences. (Then E RAG, F Watchdog, G evals, H tracing/
cost, I MCP, J deploy.)

---

## Entry 31 — Phase D: three-tier memory (Redis + pgvector) + fallback hardening; PHASE D COMPLETE
**Date:** 2026-06-27
**Phase:** Phase D (memory)

### Concepts taught
- **Three memory tiers**: short-term *conversation* (what we just said — Redis, per thread),
  long-term *facts* (home/work stop, prefs — Postgres, across sessions), and *vector* recall
  (similar-by-meaning — pgvector). Long-term + vector share one table: a fact row stores the text
  AND its embedding, so we fetch by exact key OR by meaning.
- **Embeddings for retrieval** (user already knew embeddings from ML): store each memory's vector;
  at query time embed the query and find nearest (cosine). "how do I get home?" lands near "home
  stop is Davis" with no shared words.
- **HNSW** = pgvector's approximate-nearest-neighbour index (GiST's high-dimensional cousin) —
  keeps similarity search fast as memories grow.
- **Why pgvector in the same DB**: join memory against live/PostGIS data in one query, zero new
  infra (the reason we didn't add a separate vector store).

### Decision: local embeddings (fastembed), deploy-ready
User wanted local (no quota) AND deployable. Chose **fastembed** (BAAI/bge-small-en-v1.5, 384-dim,
ONNX/CPU — no torch, no API). Runs on any CPU host (droplet). **Model baked into the api image at
build time** (Dockerfile `RUN python -c "...TextEmbedding(...)"` + `FASTEMBED_CACHE`) so production
never downloads at runtime. embeddings.py reads `FASTEMBED_CACHE` (set in Docker; None locally).

### What we did
- **D1 schema** — `0012_memory.sql`: `CREATE EXTENSION vector`; `user_memory(id, user_id, kind,
  content, embedding vector(384), created_at)` + **HNSW** cosine index + `(user_id, kind)` btree +
  UNIQUE(user_id, content) (no dup facts). pgvector 0.8.3 already in our timescaledb-ha image — no
  Neon needed locally; same extension works on Neon in Phase J.
- **D2 long-term + vector** — `embeddings.py` (lazy `lru_cache` model, `embed()` via
  `asyncio.to_thread` since fastembed is sync/CPU; `to_pgvector()` literal). `memory.py`:
  `remember` (embed + INSERT ON CONFLICT), `recall` (ORDER BY `embedding <=> query::vector`),
  `load_preferences` (exact pull of prefs/places). copilot.py: `Deps.user_id="demo"`, a dynamic
  `@copilot.system_prompt` that injects the user's saved facts every run (used unprompted), and
  `remember`/`recall` tools. Prompt requires saving **self-describing** facts ("home stop is Davis",
  not "Davis") — fixed after the model first stored a bare value.
- **D3 conversation (Redis)** — `conversation.py`: `load_history`/`save_turn` keyed
  `conv:{user}:{thread}` (list, last 12 turns, 1-day TTL), rebuilding pydantic-ai
  ModelRequest/ModelResponse. `/agent/ask` now takes optional `thread_id` → loads history into
  `message_history`, saves the new turn. (The CopilotKit chat already gets in-session memory via
  AG-UI replay; this gives the REST path durable server-side memory and teaches the tier.)

### Fallback hardening (a slice of Phase H, pulled forward — testing forced it)
Heavy agent testing exhausted Gemini Flash (250/day) → fell straight to Groq, whose Llama emits
tool calls as **`<function=name,{args}</function>` text** (not the API tool-call field), which
pydantic-ai can't parse → `UnexpectedModelBehavior`/validation errors in the chat. Fixes in
`gateway.py`:
1. Inserted **Gemini 2.5 Flash-Lite** between Flash and Groq — still Gemini (well-formed tool
   calls) + its own larger free quota, so we hit a *reliable* tier before the flaky Llama.
2. Added transient-overload markers (`503`, `unavailable`, `overloaded`, `high demand`,
   `try again later`) to `_should_fallback` so Gemini's "experiencing high demand" 503 **fails
   over** instead of surfacing (it streams in-band on a 200, so it must match by message).

### How it was verified
- `memory.py` direct test: dedup works; semantic recall correct ("how do I get home?"→Davis 0.37,
  "where do I work?"→Kendall 0.38, "do I like transfers?"→fewer-transfers 0.20).
- `conversation.py` round-trip: 2 turns → 4 typed messages rebuilt.
- Agent end-to-end (after Flash-Lite fix): "Plan a trip from Harvard to my home stop" →
  tools `recall`+`plan_trip` → Harvard→Davis (knew home unprompted). "How do I get from home to
  work?" → recalled BOTH home=Davis & work=Kendall, planned Davis→Kendall 11min, clean structured
  output. User confirmed the chat worked for several questions.
- ruff clean; api rebuilt; embedding model baked into image.

### KNOWN ISSUE (not a Phase D bug): free-tier exhaustion
After ~heavy testing, "All models from FallbackModel failed (4 sub-exceptions)" — Flash + Flash-Lite
+ Groq all out of daily free quota/tokens. This is the war story Phase H addresses (caching,
per-user rate limiting, more providers Cerebras/OpenRouter, request queue). Quotas reset daily.
Mitigation options noted for next session: fresh Gemini key, add Cerebras/OpenRouter, or just wait.

### Phase D status: ✅ COMPLETE (functionally verified). Three tiers live: conversation (Redis),
long-term (Postgres exact), vector (pgvector HNSW similarity). Single "demo" user until auth.

### Next step
Phase D **Concept Check** (name the 3 tiers + where each lives; what an embedding is + how
similarity search works; why pgvector lives in the same DB). Then **Phase E** (agentic/corrective
RAG over service alerts + policy docs with citations). Decide LLM-capacity approach for continued
testing. Pending (after all phases): model retrain + agent eval pass.

---

## Entry 32 — Phase E: agentic (corrective) RAG over alerts + policy docs; PHASE E COMPLETE
**Date:** 2026-06-27
**Phase:** Phase E (agentic RAG)

### Phase D Concept Check — PASSED (with corrections)
3 tiers named ✓ but corrected: long-term + vector are the SAME Postgres table (pgvector is IN
Postgres), differing by ACCESS (exact lookup vs `<=>` similarity) — not separate DBs. HNSW =
*approximate* NN (navigable graph, skips most vectors) ✓. #3 corrected: pgvector co-located NOT
because "Postgres stores conversation" (that's Redis) but for (a) no new infra and (b) JOIN
embeddings with relational/PostGIS data in one query.

### Concepts taught (Phase E)
- **RAG**: give the LLM a searchable library (chunk → embed → store → retrieve top-k → answer from
  sources with citations). Embedding done with LOCAL fastembed → **no LLM quota** for ingestion.
- **Plain vs agentic/corrective RAG (CRAG)**: plain = retrieve once then answer; corrective = check
  whether retrieved chunks are actually relevant, and if weak, re-query (rephrase / widen / other
  source) before answering. Retrieval inside the reasoning loop.
- **Prompt injection (2B.16)**: retrieved text is DATA, not commands — the agent reasons *about* it,
  never *follows* instructions embedded in it.

### What we did (all of E1–E3 needs zero LLM quota)
- **E1** `0013_rag.sql`: `rag_documents(id, source, title, chunk_text, embedding vector(384),
  metadata jsonb, created_at)` + HNSW cosine index + source btree + UNIQUE(source, chunk_text).
- **E2 ingestion** — curated `docs/kb/*.md` (fares, accessibility, bikes, service-hours) chunked by
  `##` heading; live MBTA `Alerts.pb` (header+description per alert). `rag.py`: `_chunk_markdown`,
  `_store` (embed + replace-by-source; **no-op on empty so a missing source never wipes data**),
  `ingest_kb` (source 'policy'), `ingest_alerts` (source 'alert', refreshes), `bootstrap`. Ran:
  16 policy + ~96 alert chunks.
- **E3** `retrieve(query,k,source)` (cosine `<=>`) + `corrective_retrieve` (judge by distance
  threshold 0.45; widen search once if weak; return chunks + `relevant`/`corrected` flags).
- **E4 agent wiring** — `search_docs` tool; system prompt: use it for fares/policy/why questions,
  answer ONLY from chunks, cite each chunk's `title` in the new `Answer.sources` field, re-query if
  relevant=false, treat retrieved text as data. Best-effort background ingest at API startup
  (`_refresh_rag` in lifespan) so the library self-populates/refreshes. Dockerfile now COPYs
  `docs/kb` into the image (else container ingest finds no files).

### How it was verified
- Retrieval (direct, quota-free): "bike on Red Line at rush hour?" → Bikes/Subway chunk 0.199
  (relevant); "subway fare/transfers?" → fare+transfer chunks 0.15/0.22; "no trains at 3am?" →
  "Why a train might not be running" 0.215; **off-topic "airspeed of a swallow?"** → relevant=false,
  corrected=true, all ≥0.5 (corrective loop works).
- Agent (LLM): "full-size bike on Red Line at rush hour?" → search_docs → correct grounded answer,
  sources cited. "subway fare + transfers?" → $2.40 + free 2h transfers, sources=["MBTA Fares… —
  Subway and bus fares", "… — Free and reduced transfers"] (specific titles after a prompt tweak).
- Startup ingest in-container confirmed: "RAG library ingested: {policy_chunks:16, alert_chunks:98}".
- ruff clean; api rebuilt.

### Notes / known
- `get_service_alerts` (live alert list by route) and `search_docs` (semantic policy/why) overlap
  for "current disruptions"; the agent usually picks sensibly. Left both (complementary).
- On a degraded fallback model a "why disrupted now" run returned a weak "Let me check…" summary —
  model-quality artifact (Phase H), not a RAG defect; good Gemini runs synthesize fully.
- Free-tier note from Entry 31 still applies; ingestion/retrieval are local (no quota), only the
  final answer needs the LLM.

### Phase E status: ✅ COMPLETE. Library: 16 policy + ~98 alert chunks in pgvector; corrective
retrieve; agent cites sources. Self-refreshes on api startup.

### Next step
Phase E **Concept Check** (plain vs agentic/corrective RAG; chunk→embed→retrieve; when/why re-query;
prompt-injection defense). Then **Phase F** (Network Watchdog — background multi-agent anomaly
detection + incident reports, supervisor/worker). Pending (after all phases): model retrain +
agent eval pass.

---

## Entry 33 — Phase H (partial, pulled forward, part 1): response caching + graceful degradation
**Date:** 2026-06-27
**Phase:** Phase H slice (rate-limit/cost engineering) — brought forward to relieve free-tier pain

### Why now (Phase E Concept Check PASSED first — all 3 correct)
Heavy same-day testing of D + E exhausted Gemini's free daily quota; the chain then falls to Groq,
whose Llama emits tool calls as `<function=name,{args}</function>` TEXT that can't be parsed → the
chat shows "tool call validation failed". Root cause = free-tier exhaustion + Groq being unreliable
for our many-tool agent. User chose to "bring part of Phase H forward" rather than just swap keys.

### What we did (no new accounts needed)
- **Response caching** (`/agent/ask`): short-TTL (90s) Redis cache keyed by
  `agentans:{user}:{sha256(question)[:16]}`. Stateless questions (no thread_id) reuse a recent
  identical answer → **no LLM call on repeats** (saves scarce quota). Don't cache memory-writes
  (skip if `remember` in tools_used) or threaded/conversational calls. Short TTL bounds staleness
  for live-data answers. Returns `cached: true` on a hit.
- **Graceful degradation** (`/agent/ask`): wrap `copilot.run` in try/except → on total
  fallback-chain failure return a clean 503 "assistant temporarily at capacity (free-tier limit)"
  instead of a raw model/validation error.

### Verified
- Asked "What are the MBTA fares for the subway?" twice → 1st hit the LLM (tools `search_docs`),
  2nd returned `cached=True` from Redis (`agentans:demo:b7508c51...`) with no model call.
- Degradation path returns the friendly 503 when models fail.
- ruff clean; api rebuilt.

### Still TODO for the chat (part 2): the chat uses the streaming AG-UI path, which caching here
does NOT cover; its real fix is **reliable extra capacity** (Llama providers mangle our tools, so
this needs a key): either a fresh-PROJECT Gemini key (separate quota) or OpenRouter. Gateway to be
made config-driven from available keys. (Full Phase H later also adds Langfuse tracing, per-user
rate limiting, request queue.)

### Next step
Wire the reliable provider once the user supplies a key, then resume **Phase F** (Watchdog).

---

## Entry 34 — Phase H (partial, part 2): multi-key Gemini rotation (reliable capacity)
**Date:** 2026-06-27
**Phase:** Phase H slice — provider chain

### Decision (user)
Don't waste keys: keep the ORIGINAL Gemini key as priority (use it first the moment its quota
resets), add new keys as backups, allow adding more later (more Google accounts/projects = more
free quota). Gemini is the only reliable free tool-caller (Groq/Cerebras Llama mangle our many-tool
calls), so chaining multiple Gemini keys is the right capacity strategy.

### What we did
- `gateway.py` now builds the FallbackModel chain **dynamically from env**: GEMINI_API_KEY
  (priority) then GEMINI_API_KEY_2, _3, ... (backups). For each key: a `GoogleProvider(api_key=...)`
  with `GoogleModel('gemini-2.5-flash')` + `('gemini-2.5-flash-lite')`. Groq stays LAST as a
  plain-text safety net. So the chain is: key1-Flash → key1-FlashLite → key2-Flash → key2-FlashLite
  → … → Groq. A 429 from an exhausted key fails over instantly (no quota consumed), so the spent
  priority key costs nothing now and auto-resumes first when it resets.
- `USAGE_LIMITS` request_limit 8 → 12 (room for fallback attempts across the longer chain).
- `.env`: added GEMINI_API_KEY_2 (new key; git-ignored). `.env.example` + docker-compose.yml:
  documented/pass GEMINI_API_KEY_2.._4. Adding a key later = edit .env + `docker compose up -d api`.

### Verified
- Old key (exhausted) → 429 → fell to NEW key's Gemini (not Groq): "elevator broken, wheelchair
  options?" → search_docs → clean grounded answer + citation "MBTA Accessibility — Elevators and
  escalators". No `<function=...>` mangling. ruff clean; api healthy.

### Phase H (partial) status: caching + graceful degradation + multi-key Gemini rotation done. Full
Phase H later: Langfuse tracing, per-user rate limiting, request queue, chat-path caching.

### Next step
User tests Phase E with 2 tough prompts on the chat, then **Phase F** (Network Watchdog).

---

## Entry 35 — Phase F: the Network Watchdog (multi-agent, supervisor/worker); PHASE F COMPLETE
**Date:** 2026-06-27
**Phase:** Phase F (multi-agent orchestration)

### Concepts taught (2B.8)
- **Multi-agent**: a SECOND agent nobody chats with, running in the background.
- **Supervisor/worker** (ours): the Copilot (supervisor) delegates an investigation to the Watchdog
  (worker). Contrasted with **planner–executor** (one plans, one executes), **reflection** (an agent
  critiques its own output), **evaluator–optimizer** (one proposes, one scores/improves).
- **The cost discipline**: detection must be cheap (no LLM); only a genuine anomaly triggers the
  LLM investigation. That split keeps a frequently-running Watchdog affordable.

### What we did
- **F1** `0014_incidents.sql`: `incidents(id, kind, route_id, severity, summary, evidence, fingerprint,
  created_at)` + recent/dedup indexes. **`anomalies.py`** (pure SQL, no LLM): bunching (BUS routes
  only — `route_type=3`, closest same-route pair within 200 m; rail "bunching" excluded as terminal/
  coupled-car noise), delays (running trips >10 min late from vehicle_arrivals), gaps (a rail line
  with no vehicles in 2 min during NY service hours 6–22).
- **F2** `watchdog.py`: a SECOND Pydantic AI agent (`output_type=IncidentReport`, tight
  `request_limit=4`) with `get_service_alerts` + a new no-key `get_weather` (Open-Meteo) tool. Given
  one anomaly it investigates and writes a report. `run_once(pool, max_incidents=3)`: detect →
  skip anomalies already logged in the last 20 min (dedup by kind/route/fingerprint) → investigate →
  store. IncidentReport schema added (kind/route/severity/summary/likely_cause). `get_weather` in
  tools.py (WMO code → words).
- **F3 supervisor delegation**: `investigate_route(route)` tool on the Copilot → detects anomalies on
  that route and runs `watchdog.investigate` → Copilot relays the report. System prompt updated.
- **F4** `GET /incidents` + `POST /watchdog/run` (manual trigger); **frontend `IncidentsPanel.tsx`**
  (polls /incidents every 30s, severity-colored, collapsible, bottom-left) mounted in AppShell.
- **F5** env-gated background loop (`_watchdog_loop` in lifespan; `WATCHDOG_ENABLED` default false,
  `WATCHDOG_INTERVAL_SECONDS` default 900) so it never burns quota unless switched on. config.py +
  docker-compose.yml wired.

### How it was verified
- Detection (quota-free): 13 candidates (8 bus bunching 13–46 m, 5 real delays 33–47 min).
- `POST /watchdog/run` → created 3 incidents; the Watchdog **actually investigated**: route 109
  cause = "construction closure on Washington St" (it called get_service_alerts and matched a real
  alert), route 111 = checked alerts+weather ("no disruptions or adverse weather"). `/incidents`
  serves them newest-first.
- **Delegation**: `/agent/ask` "have the watchdog investigate route 1" → tools_used
  `["investigate_route"]` → relayed the Watchdog's bunching report. Supervisor/worker confirmed.
- ruff clean; `tsc --noEmit` clean; api rebuilt.

### Note
Multi-key Gemini rotation (Entry 34) held up across all this testing — no manual key swaps needed.

### Phase F status: ✅ COMPLETE. Two agents: Copilot (you talk to) + Watchdog (background). Incidents
panel live in the UI. Background loop available but OFF by default.

### Next step
Phase F **Concept Check** (supervisor/worker vs planner-executor/reflection/evaluator-optimizer; how
the two agents share tools/state safely). Then **Phase G** (evals — golden set + LLM-as-judge +
trajectory checks). Pending (after all phases): model retrain + agent eval pass.

---

## Entry 36 — Bugfix: chat "Processed history must end with a ModelRequest"
**Date:** 2026-06-28
**Phase:** Phase F follow-up (Concept Check PASSED — supervisor/worker + patterns + dedup/read-only)

### Symptom
After a tool-heavy chat (e.g. a turn that drew a trip), a later message errored with
"Processed history must end with a `ModelRequest`" (pydantic-ai `_agent_graph.py:940`).

### Root cause (traced through the AG-UI adapter)
Our CopilotKit frontend action handlers (highlightRoute, dropPin, drawTrip, clearMap) returned
**void**. When the agent's final turn was text + a frontend action call, that call had no result →
"dangling". The adapter's `sanitize_messages` strips the dangling tool call but KEEPS the assistant
text, leaving the reconstructed history ending on a `ModelResponse` → the run rejects it. (A void
frontend action is also just bad CopilotKit practice — the model never sees a tool result.)

### Fix
Each handler now returns a short status string (e.g. "Highlighted route Red on the map."). The tool
call is then resolved (has a result), so it's not stripped and the continuation ends on a proper
ToolReturn (`ModelRequest`). `tsc --noEmit` clean.

### Note for re-test: refresh an already-broken chat tab to start a clean thread.

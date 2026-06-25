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

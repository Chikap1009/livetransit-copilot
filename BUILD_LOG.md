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

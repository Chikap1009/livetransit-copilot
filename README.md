# LiveTransit Copilot

**🔴 Live demo:** **[livetransit.duckdns.org/web](https://livetransit.duckdns.org/web/)** — watch Boston's MBTA move in real time and chat with the AI copilot. *(Running 24/7 on a free-tier box.)*

A real-time public-transit tracking + ML arrival-prediction platform (**LiveTransit**, the "body"),
with a production-grade **agentic AI assistant** layered on top (**the Copilot**, the "brain") that
reasons over the live data using real tools, memory, retrieval, and a map it can draw on.

---

## What it does

**Body — LiveTransit**
- Live map of the **entire MBTA network** (subway, commuter rail, bus, ferry) where **~400–800
  vehicles move in real time**, fed by a GTFS-Realtime ingestion pipeline.
- Click any stop for **predicted arrivals** from a LightGBM model (**held-out MAE 45.4s**, 85%
  better than the schedule baseline).
- Built on a streaming pipeline: **poller → Redis Streams → processor → PostGIS/TimescaleDB →
  WebSocket fan-out**, with **vector map tiles** (Martin) and spatial/time-series indexing.

**Brain — the Copilot** (a [Pydantic AI](https://ai.pydantic.dev) ReAct agent)
- **9 real tools** over the live data: `get_vehicle_positions`, `predict_eta`, `plan_trip`
  (rail routing with transfers), `get_service_alerts`, `search_docs`, `investigate_route`,
  `remember`, `recall`, `get_weather`.
- **3-tier memory** (pgvector): durable user facts, per-conversation history (Redis), preferences.
- **Corrective RAG** over agency policy docs + live alerts, with citations.
- A background **Network Watchdog** — a second agent that detects anomalies (bunching, gaps,
  delays) and writes incident reports.
- **Streaming generative UI**: the agent draws routes/pins on the map as it reasons.
- **Resilience**: a multi-key **Gemini → Groq** fallback chain, response caching, and per-IP rate
  limiting; **evals** (pydantic-evals) and **tracing** (Langfuse via OpenTelemetry).
- Also exposed over **MCP** (Model Context Protocol) so Claude Desktop / Cursor can drive it.

---

## Architecture

```
                         ┌─────────────── Oracle Always-Free VM (Docker) ───────────────┐
  MBTA GTFS-RT ──poller──►  Redis Streams ──processor──►  PostGIS + TimescaleDB + pgvector │
                         │        │                                   ▲                    │
   browser ◄─WebSocket───┤      FastAPI  ──┬── REST / WS / SSE ───────┘                    │
   (live map + chat)     │      (api)      ├── Pydantic AI agent (tools, memory, RAG)      │
        ▲                │                 └── Watchdog agent (background)                 │
        │  HTTPS         │      Martin (vector tiles) · Caddy (auto-TLS)                   │
        └────────────────┴──────────────────────────────────────────────────────────────-┘
   Observability: Prometheus + Grafana (body) · Langfuse (agent)   |   LLM: Gemini→Groq fallback
```

## Tech stack

| Layer | Tech |
|---|---|
| **Data** | PostgreSQL + **PostGIS** (spatial) + **TimescaleDB** (hypertables) + **pgvector** (HNSW) |
| **Streaming / cache** | **Redis** (Streams, caching, rate limiting) |
| **API** | **FastAPI** (async), WebSockets, SSE |
| **Tiles / map** | **Martin** vector tiles, **MapLibre GL JS** |
| **ML** | **LightGBM** delay-propagation model (time-based split) |
| **Agent** | **Pydantic AI** (ReAct, structured outputs, FallbackModel), **fastembed** (local embeddings) |
| **Frontend** | static live map (`frontend/`) + **Next.js + CopilotKit** generative UI (`web/`) |
| **Ops** | **Docker Compose**, **GitHub Actions** CI, **Prometheus/Grafana**, **Langfuse**, **MCP** |
| **Deploy** | Oracle Cloud Always-Free VM · **Caddy** auto-HTTPS · **DuckDNS** · free tiers end-to-end |

## Key metrics

| | |
|---|---|
| Spatial query speedup (GiST index) | **~60×** (89 ms → 1.4 ms) |
| ETA model MAE (held-out) | **45.4 s** — vs 313.3 s schedule, 53.9 s persistence baselines |
| Ingestion | ~40 positions/sec, **0 poll failures**, idempotent exactly-once |
| Deployment | **24/7 on $0** (Oracle Always-Free 1 GB box) |

See [`METRICS.md`](METRICS.md) for methodology and [`docs/deployment.md`](docs/deployment.md) for
the deployment write-up + observability proof.

## Deployment notes (an honest engineering story)

Getting this live 24/7 on **$0** meant matching a *continuous ingestion* workload to free-tier
pricing models. Managed serverless tiers (Neon, Upstash) are priced for **bursty, mostly-idle**
apps — a live transit tracker never sleeps — so the data layer runs **co-located on the always-on
compute** instead. HTTPS is handled by **Caddy** (auto Let's Encrypt) behind a free **DuckDNS**
domain. The full reasoning, and **proof of the observability stack that's omitted from the 1 GB
prod box** (live Grafana dashboard, charts from real Prometheus data), is in
[`docs/deployment.md`](docs/deployment.md).

## Local development

```bash
cp .env.example .env          # fill in your keys (Gemini/Groq for the agent)
docker compose up -d --build  # postgres, redis, api, poller, processor, tiles, prometheus, grafana
bash ops/deploy/init_db.sh    # apply migrations + load static GTFS
# live map:  http://localhost:8000/web/      metrics: http://localhost:3001 (Grafana)
```

## Repository layout

| Path | What |
|---|---|
| [`backend/`](backend/) | FastAPI app, ingestion, ML, and the agent (`backend/app/agent/`) |
| [`db/`](db/) | SQL migrations + the static GTFS loader |
| [`frontend/`](frontend/) | the static live-map page (served at `/web`) |
| [`web/`](web/) | Next.js + CopilotKit generative-UI chat |
| [`ops/`](ops/) | Prometheus/Grafana config + deploy helpers (Caddy, DB bootstrap) |
| [`docs/`](docs/) | knowledge base, MCP guide, deployment write-up + proof |
| [`LiveTransit_Copilot_Build_Bible.md`](LiveTransit_Copilot_Build_Bible.md) · [`BUILD_LOG.md`](BUILD_LOG.md) | the spec + a detailed running build log |

## Data & attribution

Live + static transit data from the **MBTA** under the MassDOT Developers License Agreement.
Built as a learning project, phase by phase (see the Build Bible).

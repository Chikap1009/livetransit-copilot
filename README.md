# LiveTransit Copilot

> A real-time public-transit tracking and ML arrival-prediction platform (**LiveTransit**, the
> "body"), with a production-grade **agentic AI assistant** layered on top (**the Copilot**, the
> "brain") that reasons over live transit data using real tools, memory, retrieval, and a map it
> can draw on.

**Status:** 🚧 Under construction — Phase 0 (foundations). This README is a stub and will be
polished at the end (see Part 6 of the Build Bible).

## What this will be
- **Body (LiveTransit):** live map of Boston's MBTA network where vehicles move in real time,
  backed by a GTFS-Realtime ingestion pipeline (Redis Streams), PostGIS/TimescaleDB storage with
  spatial + time-series indexing, WebSocket fan-out, vector map tiles, and a LightGBM arrival
  predictor.
- **Brain (Copilot):** a Pydantic AI ReAct agent with real tools over the live data, three-tier
  memory (pgvector), corrective RAG, a background "Network Watchdog" agent, evals, tracing, and a
  chat UI that draws routes on the map.

## Build plan
See [`LiveTransit_Copilot_Build_Bible.md`](LiveTransit_Copilot_Build_Bible.md) — the complete
specification, concept textbook, and phase-by-phase plan. Progress is logged in
[`BUILD_LOG.md`](BUILD_LOG.md).

## Local setup
_Coming in Phase 0+: `docker compose up` will bring up the local stack._

## Data & attribution
Transit data from the **MBTA** under the MassDOT Developers License Agreement.

# LiveTransit Copilot — The Complete Build & Learning Bible

> A real-time public-transit tracking and ML arrival-prediction platform (**LiveTransit**, the "body"), with a production-grade **agentic AI assistant** layered on top (**the Copilot**, the "brain") that reasons over live transit data using real tools, memory, retrieval, and a map it can draw on.
>
> This single document is the complete specification, the concept textbook, and the step-by-step build plan. It is written to be the **first message in a Claude Code session** and the permanent source of truth in the repo.

---

## PART 0 — Instructions for Claude Code (read first, follow always)

**You are my pair-programmer for this entire project. I (the human) am the engineer. You explain; I understand; then we build. This is the most important rule in this document and it overrides any urge to be fast.**

These rules are in force for every single step of every phase, for the whole project:

1. **Explain before you execute.** Before running any command, creating or editing any file, or installing anything, first explain in plain language: what it is, what it does, *why* we need it here, how it fits the bigger picture, and what would break without it. Then wait for my explicit "go" before doing it. Never batch-execute multiple unexplained steps.
2. **One new concept at a time.** If a step introduces more than one unfamiliar idea, stop and teach each idea separately before we proceed. Assume I am new to backend engineering and to agentic AI. I know Python and machine learning well; I do not yet know systems, databases, web backends, or how agents work.
3. **No jargon without a plain-language definition** the first time it appears. Use analogies.
4. **After each step, tell me how to verify it worked** (the exact command to run or thing to check, and what a correct result looks like).
5. **Show me the file tree / what changed** after edits, so I always know the current state of the repo.
6. **If I paste an error, diagnose it with me** — explain the likely cause and the fix before applying it.
7. **Never put secrets in the repo.** API keys, database URLs, and passwords go in a git-ignored `.env` locally and in the platform's secret store in production. Flag it loudly if we're ever about to commit one.
8. **Keep scope tight.** Don't add features, abstractions, or dependencies we didn't agree on. If you think something extra is worth it, propose it and wait.
9. **Prefer teaching the standard tool over a clever shortcut.** I'm here to learn the things interviewers ask about, not to finish fastest.
10. **At the end of each phase, quiz me** with that phase's "Concept check" so we confirm I actually learned it before moving on.

**How we work through this document:** we go phase by phase, in order (Part 5). At the start of a phase I'll paste its "Kickoff prompt." You acknowledge the rules above, teach the phase's "Learn first" concepts, then we build the "Steps" together, verifying as we go. We do not skip ahead.

**Acknowledge that you've read and understood these rules, then ask me which phase we're starting (it will normally be Phase 0).** The rest of this document is the full specification for your reference.

---

## PART 1 — The project, from zero

### 1.1 What we are building, in plain language
Two layers that together make one product.

**Layer 1 — LiveTransit (the body).** A website with a live map of a city. Every bus and train is a dot that moves in real time as the actual vehicle moves. Click a stop and it shows "next train: 4 minutes" — and that number is a prediction from a small machine-learning model *we* train on historical data, not a value copied from the transit agency. Behind the map is real backend engineering: continuously pulling in a firehose of live vehicle positions, storing it efficiently, answering spatial questions fast ("what's near me?"), pushing updates to many users at once, and predicting arrivals.

**Layer 2 — the Copilot (the brain).** An AI assistant you talk to in plain English ("Can I get from Kendall to the airport in 40 minutes, and is the Red Line a mess right now?"). It is **agentic**: it decides for itself which of the system's real tools to use, in what order, calls them, reads the results, and answers — while drawing the route and highlighting delays on the map. It remembers your preferences, looks things up in a document library when needed, and shows its reasoning live as it works. A second background agent (the "Network Watchdog") continuously watches the feed for problems and writes incident reports.

We build the body first, then the brain on top of it. The brain is only impressive because it acts on the real, live system underneath.

### 1.2 Why this exact project
- **It proves two things at once.** Most candidates can either build a system *or* talk vaguely about AI. This proves you can build a real full-stack, real-time, data-intensive backend **and** that you deeply understand modern agentic AI and can ship a full agentic application. That combination is uncommon and makes interviewers lean in.
- **It's different from my other work.** (My résumé already has two model-centric deep-learning research projects — a Mamba state-space-model video-grounding architecture, and an audio deepfake/anti-spoofing pipeline.) This is a *systems + agents* project, not a third "train a model" project, giving real résumé diversity.
- **It hits the in-demand 2025–2026 keyword clusters** twice over: backend (PostgreSQL/PostGIS, Redis, Docker, WebSockets, streaming pipelines, CI/CD, observability, cloud deploy, spatial indexing, time-series) and agentic AI (agent loop, tool calling, structured outputs, memory, agentic RAG, multi-agent orchestration, MCP, evals, tracing, streaming generative UI).
- **It's visually striking and uncommon.** A live map at a public URL where an AI assistant draws your route and explains delays in real time is something a reviewer can see and click in ten seconds.
- **It decomposes into teachable phases**, which is exactly how I want to learn it (understanding every step rather than vibe-coding).
- **It's buildable entirely on free tiers** and deployable live, on a laptop with a modest GPU, because the heavy AI model is hosted, not local.

### 1.3 What I'll be able to claim and defend when it's done
Backend: designed a multi-service backend with decoupled ingestion/processing/serving; ingested a real-time protobuf feed with idempotency, rate limits, backpressure; modeled and indexed geospatial + time-series data in PostgreSQL with PostGIS, TimescaleDB and H3; built WebSocket fan-out; served vector map tiles to a MapLibre frontend; trained and served an ML arrival predictor; containerized with Docker; set up CI/CD; added Prometheus/Grafana observability; deployed live on free infrastructure.

Agentic AI: built a tool-calling ReAct agent over live geospatial data with seven real tools; structured outputs with validation; three-tier memory (conversation, long-term, vector) with pgvector; corrective agentic RAG over service alerts and policy docs; a supervisor/worker multi-agent setup (the Watchdog); an MCP server exposing the tools; an evals harness (golden set, LLM-as-judge, trajectory checks); Langfuse tracing; multi-provider LLM fallback with caching and rate limiting for a public app; and a streaming generative UI fused with the map.

### 1.4 The end-state vision (what "finished" looks like)
A public URL where a map loads with the city's transit network (routes + stops as vector tiles); live vehicle dots move across it via WebSocket; a chat panel lets you ask anything in English; the assistant streams its reasoning and tool steps, draws routes and isochrones and highlights vehicles on the map, and answers with cited, structured results; clicking a stop shows your model's predicted arrivals with an accuracy panel vs. the agency baseline; a background Watchdog posts live incident reports; and a linked Grafana dashboard plus a Langfuse trace view show the system's health and the agent's inner workings. The README explains it, links the live demo, shows real metrics, and offers one-command local setup.

> **Scope reassurance:** Phases 0–3 alone already make a strong project (a live transit map). Adding the ML (Phase 6) and the first agent (Phases A–C) makes it impressive. Everything else raises the ceiling. If time gets tight, a complete subset still tells a great story.

---

## PART 2 — The concept textbook

> Skim this once to build vocabulary, then return to the relevant subsection when its phase arrives — that's when it clicks. Nothing here is optional knowledge for a backend/agentic engineer. Section 2A is the backend (the body); Section 2B is agentic AI (the brain).

## Section 2A — Backend & systems concepts

### 2A.1 Frontend, backend, client, server
A **client** makes a request (your browser). A **server** listens for requests and responds (your code, running somewhere). The **frontend** runs in the user's browser (HTML/CSS/JavaScript — the map and chat). The **backend** is everything else: server code, database, data pipeline, the agent. This project is mostly backend, which is the point.

### 2A.2 HTTP: the request/response model
The web runs on **HTTP**: the client sends a *request* (a method like `GET`/`POST`, a URL, headers, optional body) and the server sends a *response* (a status code like `200 OK` or `404 Not Found`, headers, a body). Key fact: **a normal HTTP request is one question and one answer, then it closes** — which is why it alone can't show a dot moving live (see 2A.13).

### 2A.3 What an API is; REST
An **API** is a contract: "send a request shaped like *this*, get data shaped like *that*." A **REST API** exposes *resources* at URLs acted on by HTTP methods, e.g. `GET /vehicles`, `GET /stops/{id}/arrivals`, `GET /routes/{id}`. Good API design (clear paths, sensible status codes, pagination, versioning) is a real interview topic you'll learn by doing.

### 2A.4 JSON and Protobuf
**JSON** is human-readable text (`{"id": 7, "lat": 42.3}`) — easy, a bit bulky. **Protobuf** (Protocol Buffers) is a compact *binary* format: smaller and faster, but needs a schema and a library to decode. **GTFS-Realtime feeds are protobuf**, so an early real skill is decoding a binary feed into usable objects with the `gtfs-realtime-bindings` library.

### 2A.5 Databases, SQL, the relational model
A **database** stores data durably and queries it efficiently. A **relational database** (PostgreSQL — "Postgres") uses **tables** (rows/columns) with relationships (a `trips` row points to a `routes` row), queried with **SQL** (`SELECT route_id, COUNT(*) FROM trips GROUP BY route_id;`). You'll learn schemas, primary/foreign keys, joins, indexes, `EXPLAIN ANALYZE` (seeing *why* a query is slow), and transactions. Postgres is the most-loved general database in industry — a major keyword.

### 2A.6 Spatial data and PostGIS
Locations need geometry, not plain numbers. **PostGIS** turns Postgres into a *spatial database*: geometry/geography column types and functions like `ST_DWithin` (within a distance), `ST_Contains` (point in polygon), `ST_Distance`. "Find vehicles within 500 m of this corner" becomes one fast query. Learn: **coordinate reference systems** (WGS84 / SRID 4326 = GPS lat-long; Web Mercator / 3857 = web maps), **geometry vs geography**, and the `geometry(Point, 4326)` column (note PostGIS points are `(lon, lat)` = `(x, y)`).

### 2A.7 Indexes — why "near me" is slow without one
An **index** is a side structure that lets the database skip scanning every row — like the index at the back of a textbook. Without one, "vehicles near X" computes distance to *every* vehicle. PostGIS builds a **GiST** spatial index (R-tree style: groups nearby things into bounding boxes so whole regions are skipped). You'll `CREATE INDEX ... USING GIST (geom)` and *watch* `EXPLAIN ANALYZE` switch from a sequential scan to an index scan — seeing a query drop from hundreds of ms to single-digit ms is when indexing clicks.

### 2A.8 H3: hexagonal spatial indexing
**H3** (from Uber) divides the world into hexagons, each a stable 64-bit ID, at multiple resolutions. Hexagons are nice because every neighbor is equidistant and cells are uniform-area and hierarchical. You'll tag each vehicle with its H3 cell, so "vehicles in my neighborhood" becomes "vehicles whose H3 id = mine" — instant aggregation, no geometry math. A recognizable résumé keyword.

### 2A.9 Time-series data and TimescaleDB
Positions arrive constantly, stamped with time — **time-series data**. **TimescaleDB** (a Postgres extension) stores it efficiently via **hypertables** (auto-partitioned by time), with **retention policies** (auto-delete old data) and **continuous aggregates** (auto-updating rollups). You'll use it to store position history for the ML model while keeping storage bounded.

### 2A.10 Caching and Redis
A **cache** stores the result of an expensive operation so you don't recompute it. **Redis** is an in-memory store used as a cache (and more). If 50 users ask "vehicles near downtown" within a second, compute once, cache in Redis for a few seconds, serve the rest from cache. Learn: cache keys, **TTL** (expiry), hit/miss ratio, and the stale-data trap.

### 2A.11 Streaming, queues, Redis Streams
A **stream/queue** is a conveyor belt between two parts of the system. The producer (poller) drops items on; the consumer (processor) takes them off at its own pace. This gives **decoupling** (parts don't run in lockstep), **backpressure** (bursts wait on the belt instead of being lost), and **resilience** (a crashed consumer doesn't lose items). You'll use **Redis Streams** with **consumer groups**. Two must-know ideas live here: **idempotency** (processing the same item twice must not corrupt state — dedupe by `(vehicle_id, timestamp)`), and **at-least-once delivery** (queues usually deliver an item *at least* once, possibly more — which is exactly why idempotency matters).

### 2A.12 Why the poller is a separate process
If the website fetched the feed on every page load, 100 visitors = 100 fetches/sec hammering the agency, and with zero visitors you'd collect no history. So a dedicated **poller** (a long-running worker that only fetches the feed on a loop) is separate from the **API** (which answers user requests). *Background work vs request handling* is a foundational backend pattern.

### 2A.13 WebSockets and fan-out
A normal HTTP request can't show live movement. A **WebSocket** stays open, so the server can **push** data whenever something changes — the dot moves on its own. The résumé-worthy idea is **fan-out**: the poller fetches the feed *once*, and that single fetch updates *every* connected browser. One upstream request serves a hundred viewers. (**Server-Sent Events / SSE** is a simpler one-directional alternative; you'll understand the trade-off.)

### 2A.14 Map rendering and vector tiles
Browsers can't load a whole city's geometry at once. **Vector tiles** slice the map into small squares, each holding just that area's geometry at that zoom, encoded compactly (MVT). A tile server (**Martin** or **pg_tileserv**, which generate tiles straight from PostGIS) serves them on demand; **MapLibre GL JS** (free, open-source) renders and styles them in the browser. You'll learn how web maps actually work.

### 2A.15 Containers, Docker, docker-compose
A **container** packages an app with everything it needs so it runs identically on your laptop and in the cloud (killing "works on my machine"). **Docker** builds/runs containers; **docker-compose** runs several together (Postgres + Redis + API + workers + tiles) with one command via `docker-compose.yml`. This is how you'll run the whole stack locally and how teams ship software. Huge keyword.

### 2A.16 Environment variables, config, secrets
Passwords, API keys, database URLs must never be hard-coded or committed. They live in **environment variables** (a git-ignored local `.env`, and the platform's secret store in production). You'll learn config separation — a discipline that, done wrong, gets people fired.

### 2A.17 Git and GitHub
**Git** is version control (tracks every change; branch and revert). **GitHub** hosts the repo and runs automation. You'll learn the everyday loop: `branch → commit → push → pull request → merge`, plus good commit messages. Recruiters look at your GitHub.

### 2A.18 CI/CD with GitHub Actions
**CI** (Continuous Integration) auto-runs tests and linters on every push. **CD** (Continuous Deployment) auto-deploys when they pass. **GitHub Actions** runs these workflows in the cloud (YAML under `.github/workflows/`). You'll set up lint → test → build image → deploy.

### 2A.19 Testing: the pyramid
**Unit tests** check one function (fast, many). **Integration tests** check parts together, e.g. the API against a real test database (fewer, slower). **End-to-end tests** check the whole flow (fewest). You'll use **pytest**. The point isn't 100% coverage; it's learning *what's worth testing* (idempotency logic, prediction math, the agent's tool use) and gaining confidence to change code without fear.

### 2A.20 Observability: logs, metrics, dashboards
You can't fix what you can't see. **Logs** are timestamped text records. **Metrics** are numbers over time (events/sec, latency, feed age). **Prometheus** scrapes/stores metrics; **Grafana** draws dashboards. You'll instrument services to *show* health with graphs — also a great demo artifact.

### 2A.21 The ML piece: regression and gradient boosting
The arrival predictor outputs a number (seconds) → **regression**. You'll engineer **features** (current delay, time-of-day, day-of-week, segment travel times, weather), split data by *time* into train/test (never random — that leaks the future), train a **gradient-boosted tree** model (**LightGBM**), and evaluate with **MAE** (mean absolute error, in seconds) against a **baseline** (schedule, historical average). Trees beat a neural net here: minutes to train on CPU, no GPU, interpretable, right-sized — showing that judgment is a strength after two deep-learning projects.

### 2A.22 GTFS and GTFS-Realtime (the data)
Agencies publish data in **GTFS** (General Transit Feed Specification), an open standard, in two flavors. **Static GTFS** is the *schedule* — a zip of CSV-like files (`routes.txt`, `trips.txt`, `stops.txt`, `stop_times.txt` (the big one), `shapes.txt` (route paths), `calendar.txt`) — your skeleton, changes rarely. **GTFS-Realtime (GTFS-RT)** is *now*, as **protobuf** at fixed URLs refreshed every several seconds, in three message types: **VehiclePositions** (where each vehicle is), **TripUpdates** (predicted arrivals/delays), **Alerts** (disruptions). Static and realtime join on shared IDs (`trip_id`, `stop_id`, `route_id`) — that join is the heart of the app and the substrate the agent's tools reason over.

---

## Section 2B — Agentic AI concepts (the brain)

### 2B.1 The big idea: program vs chatbot vs agent
A **normal program** does exactly the steps you wrote, in order, every time — it can't improvise. A **plain chatbot** (a language model alone) talks fluently but can't *do* anything or look anything up — ask where bus 77 is and it guesses, because all it has is text it learned in training. An **agent** is the chatbot's brain *plus* real tools *plus* permission to decide which tools to use. Now it calls a real function, reads the live answer, and tells the truth. That loop is the entire trick; everything else makes the loop smarter, safer, and presentable.

### 2B.2 The agent loop (ReAct: reason → act → observe)
The core mental model, and usually the first interview question. The agent **reasons** about what's needed, **acts** by calling a tool, **observes** the result, then reasons again — looping until it can answer. "ReAct" = Reasoning + Acting. If you can't draw this loop, you're filtered out. In this project: the Copilot reads your question, decides it needs live positions, calls a tool, observes, maybe calls another, then answers and draws on the map.

### 2B.3 Tools and function calling
A **tool** is a normal function that does one real thing, exposed to the model. **Function calling** (a.k.a. tool calling) is how the model uses it: you describe each tool (name, purpose, inputs — auto-generated from your code), and when the model decides to use one it outputs a structured "call `get_vehicle_positions` with route='Red'" message; your program runs the function and feeds the result back. The model never runs code itself — your code does, on its instruction. This is *the* most-demonstrable agentic skill, and you'll have seven real examples. The project's tools: `get_vehicle_positions`, `predict_eta` (your LightGBM model), `query_spatial` (English → safe PostGIS), `get_service_alerts`, `plan_trip`, `compute_isochrone`, `get_weather`.

### 2B.4 Structured outputs
A model alone replies with free-form prose, which programs can't reliably use. A **structured output** forces it to fill a defined form instead, e.g. a trip plan returns `{legs: [...], total_minutes: 38, transfers: 1}`. You define the shape (a Pydantic schema); if the model returns something malformed, the system catches it and makes the model fix it. This is the line between a flaky demo and something dependable, and it's the bridge to the rest of the app (the map can only draw a route from clean, labeled data).

### 2B.5 The framework: Pydantic AI (and why)
You *could* hand-write the loop (call model → read tool request → run tool → feed back → repeat), but that's fiddly plumbing. A **framework** is pre-built scaffolding so you focus on the interesting parts. **Pydantic AI** is "FastAPI for agents," by the team whose validation library underlies most industry AI tools — so it fits your Python/FastAPI backend. It lets you: declare a tool with a `@agent.tool` decorator on a normal function (auto-writes the tool description); guarantee structured outputs with auto-retry on malformed results; switch model providers by changing **one string** (this powers the fallback chain); stream steps; and plug in tracing and evals. In-demand, teachable, free-tier-friendly. (You'll also *learn the concepts* of **LangGraph** — graph-based orchestration with checkpointing — so you can speak to it in interviews, optionally implementing the Watchdog in it.)

### 2B.6 Memory (three kinds) + embeddings + pgvector
A raw model forgets everything between messages. Real agents have three memories:
- **Short-term (conversation) memory** — what was said earlier *in this chat*, so "what about the way back?" makes sense. Stored in **Redis**, keyed per conversation.
- **Long-term memory** — facts *across days*: your home/work stops, preference for fewer transfers. Persisted in the database.
- **Vector memory** — recall of *similar past situations* by meaning. Needs two ideas: an **embedding** turns text into a list of numbers capturing meaning (same idea as embeddings in your ML work, used here for retrieval — similar meaning → numbers close together); a **vector store** keeps these and instantly finds the closest. You'll use **pgvector**, an add-on to your existing Postgres (HNSW index) — *no new infrastructure*, and you can join embeddings against relational/PostGIS data in one query. Vector memory lets the agent recall "last time the Red Line had a signal issue at rush hour…". It's also the basis for RAG.

### 2B.7 RAG and agentic RAG
The model only knows its training data, not your live alerts or agency policies. **RAG (Retrieval-Augmented Generation)** gives it a searchable document library: chunk the docs, embed them into pgvector, and at question time retrieve the most relevant chunks and hand them to the model so it answers from real sources with citations. Plain RAG = "search once, then answer." **Agentic RAG** is the smarter, interview-expected version: the agent *checks whether what it retrieved is actually relevant*, and if not, searches again (rephrasing, or a different source) before answering — retrieval becomes part of the thinking loop. This is the **corrective-RAG (CRAG)** pattern. Your library: service alerts, GTFS reference docs, agency policy pages — so the agent can explain *why* a line is disrupted, with citations.

### 2B.8 Multi-agent orchestration (the Network Watchdog)
Beyond the one agent you talk to, you'll add a second one no one talks to — the **Network Watchdog** — that runs in the background, watching the live feed for problems (bus *bunching*: two arriving together with a long gap after; unusual delays; service gaps), investigates by calling the same tools (+ weather), and writes human-readable incident reports. Two agents are enough to *demonstrate* **multi-agent orchestration** without an unaffordable, hard-to-debug swarm. The pattern here is **supervisor/worker** (the Copilot can delegate to the Watchdog). Be able to *name and contrast* the others in interviews: **planner-executor** (one plans, one executes), **reflection** (an agent critiques its own output), **evaluator-optimizer** (one proposes, one scores and improves).

### 2B.9 MCP (Model Context Protocol)
**MCP** is a recent open standard — "a USB-C port for AI tools." Expose your LiveTransit tools as an **MCP server** and *any* MCP-compatible app (Claude Desktop, Cursor, others) can plug in and use them without custom glue. Architecturally it offers **Tools**, **Resources**, and **Prompts** over JSON-RPC, with a **Streamable HTTP** transport. It's a standout résumé signal (backed by Anthropic, OpenAI, Google, the Linux Foundation) and a memorable demo: "here's Claude Desktop driving my transit system through MCP." Optional polish, high impact.

### 2B.10 Streaming agent output
If the agent goes silent for ten seconds, the app feels broken. **Streaming** sends progress to the screen as it happens — the answer text appears word by word, and (crucially) the tool steps show live ("Checking live vehicles… predicting arrival… drawing route"). This visible reasoning trace is both good UX and the core "wow" — the user *sees* the agent work, which is what makes an agentic app look impressive rather than like a search box.

### 2B.11 Evals (the hot topic)
An **eval** is a repeatable test of agent quality. Build a **golden set** of ~50–100 example questions with known good behavior and run the agent against them after every change to catch regressions. The subtlety: check not just whether the *final answer* is right but whether the agent took a *sensible path* — right tools, reasonable order, no pointless loops (**trajectory evaluation**). You'll also use **LLM-as-judge** — a model with a clear rubric scoring answers at scale — via **Pydantic Evals** and/or Langfuse datasets. Talking confidently about evals puts you ahead of most candidates, who can build agents but not measure them. (Honest note: writing a good golden set is the most underrated effort — a single quality case can take an hour.)

### 2B.12 Tracing / observability for agents (Langfuse)
"It gave a weird answer" isn't debuggable alone. **Tracing** records every step — each model call, tool call, and retrieval, with inputs, outputs, timing, and token counts — as a nested, replayable timeline. You'll use **Langfuse** (free Hobby tier, or self-host via Docker). It's the black-box recorder for the agent: find the unnecessary triple weather-call, the slow tool, the rising cost. (This is the agentic cousin of Prometheus/Grafana from 2A.20.)

### 2B.13 The LLM "brain": hosted models, free tiers, fallback
The brain is a **Large Language Model** (like ChatGPT/Claude). You don't train it — you *use* an existing one over the internet. It runs **hosted** (on the provider's servers), for two reasons: your 4060/8GB can't run a model this capable, and a public deployed app needs a model reachable from the server. Primary: **Google Gemini 2.5 Flash** (free tier, supports function calling and structured outputs). The catch is **rate limits** — caps per minute/day — and an agent loop makes many model calls per question, so a public app can hit them. The fix is a **fallback chain**: if one provider is maxed, automatically switch to the next (Gemini → Groq → Cerebras → OpenRouter). Pydantic AI makes switching a one-string change, which also insulates you from the frequent free-tier changes (see Part 7 for current limits and the December 2025 Gemini cut).

### 2B.14 Cost & rate-limit engineering (for a public agent)
Because the brain is free-tier and the app is public, be deliberate so a few users don't exhaust the daily quota: **caching** (reuse a recent identical answer instead of re-running the whole loop), **per-user rate limiting** (one person can't spam it), the **fallback chain** (switch brains when maxed), **capping tool-call depth** per question (Pydantic AI usage limits), and a **request queue** under load. "I made an agent reliable under free-tier limits" is a genuine engineering war story, not a toy.

### 2B.15 Generative UI & map fusion (the frontend magic)
**Generative UI** = the agent generates interface pieces on the fly (a clean trip-plan card, an incident-report card) instead of dumping text. **Map fusion** = the agent acts on the map (drops pins, draws routes, highlights delayed vehicles, shades reachable areas). You'll use **CopilotKit** (with its AG-UI protocol), a library built for in-app copilots: it lets the agent see what's on the user's screen (`useCopilotReadable`), trigger frontend actions (`useCopilotAction`, e.g. "draw this route"), and render live agent state — and it bridges a React/Next.js frontend to your Python agent backend. The combination (chat + visible reasoning + a map the AI draws on) is what reads instantly as "this person can build a real agentic product."

### 2B.16 Guardrails & safety (especially text-to-PostGIS)
Letting a model generate database queries is powerful and dangerous. Guardrails for the `query_spatial` tool: run it under a **read-only** database role, **allow-list** the tables/columns it may touch, set a **statement timeout**, and never interpolate model text directly into SQL without validation. More broadly: validate inputs/outputs, and be aware of **prompt injection** — malicious instructions hidden inside retrieved text (e.g. a service-alert field) trying to hijack the agent — so treat retrieved content as data, not commands. **Human-in-the-loop** (pausing for confirmation before an expensive/ambiguous action) is the safety valve for higher-risk tools.

---

## PART 3 — Architecture & full tech stack

### 3.1 The two-layer system (how it all connects)
**Body (LiveTransit):** a *poller* fetches the GTFS-RT protobuf every ~10s and publishes to a *Redis Stream*; a *processor* dedupes, H3-tags, and writes to *PostGIS/TimescaleDB*; the *API* serves REST + a *WebSocket* fan-out; a *tile server* serves vector tiles; the *MapLibre frontend* renders the network and live dots; the *ML predictor* serves ETAs; *Prometheus/Grafana* observe it.

**Brain (Copilot), layered on top:** an *agent service* (Pydantic AI) wraps the body's capabilities as *tools*; an *LLM gateway* routes to Gemini→Groq→Cerebras→OpenRouter; *pgvector* (in the same Postgres) holds long-term + vector memory and the RAG document index; *Redis* holds conversation memory; a *Watchdog* agent runs in the background; *Langfuse* traces every agent step; an *MCP server* exposes the same tools externally; the *Next.js + CopilotKit frontend* streams reasoning and lets the agent draw on the MapLibre map.

```
                         ┌─────────────────────────── BRAIN (Copilot) ───────────────────────────┐
  user (English) ─▶ Next.js + CopilotKit UI ─▶ Agent service (Pydantic AI, ReAct loop)
                         │                              │        │            │
                         │              LLM gateway ◀───┘        │            └─▶ MCP server (external apps)
                         │   (Gemini→Groq→Cerebras→OpenRouter)   │
                         │                                       ▼
                         │                                  TOOLS (call the body) ──┐
                         │                                                          │
                         │   memory: Redis (conversation) + pgvector (long-term,    │
                         │           vector, RAG docs)   ── Langfuse traces all ──   │
                         └──────────────────────────────────────────────────────────┘
                                                                                     ▼
  ┌──────────────────────────────── BODY (LiveTransit) ───────────────────────────────────┐
  feed ─▶ Poller ─▶ Redis Stream ─▶ Processor ─▶ PostGIS + TimescaleDB ─┬─▶ WebSocket ─▶ map
                                       (dedupe, H3)        ▲             ├─▶ ML predictor (ETAs)
                                                           │             └─▶ Tile server ─▶ MapLibre
                                       LightGBM trains on history;  Prometheus + Grafana observe all
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

The agent's tools are thin functions that call the body: `get_vehicle_positions` reads PostGIS; `predict_eta` calls the LightGBM service; `query_spatial` runs guarded text-to-PostGIS; `get_service_alerts` reads alerts; `plan_trip`/`compute_isochrone` call OpenTripPlanner/OpenRouteService; `get_weather` calls Open-Meteo. The agent reasons; the body does the real work.

### 3.2 Component responsibilities
| Component | Responsibility | Lives where |
|---|---|---|
| Poller (worker) | Fetch GTFS-RT ~10s, decode, publish to stream | Backend, always-on |
| Redis Stream | Buffer between fetch and process | Redis (Upstash) |
| Processor (worker) | Dedupe, H3-tag, write positions, rollups | Backend, always-on |
| API server | REST + WebSocket endpoints | Backend (FastAPI) |
| ML predictor | Train offline; serve ETAs online | Backend (LightGBM in memory) |
| Tile server | Vector tiles from PostGIS | Martin / pg_tileserv |
| Database | Static GTFS + recent positions + history + pgvector memory/RAG | Postgres/PostGIS/Timescale/pgvector (Neon) |
| Agent service | ReAct loop, tool registry, supervisor + Watchdog, structured outputs, guardrails, usage limits | Backend (Pydantic AI) |
| LLM gateway | Route to provider with fallback | Backend (Pydantic AI / LiteLLM-style) |
| MCP server | Expose tools over MCP (Streamable HTTP) | Backend (FastMCP / Pydantic AI MCP) |
| Memory | Conversation (Redis) + long-term/vector + RAG (pgvector) | Redis + Neon |
| Tracing | Record every agent step | Langfuse (cloud free or self-host) |
| Frontend | Map + live dots + chat + generative UI + map fusion | Next.js + React + MapLibre + CopilotKit (Cloudflare Pages) |
| Observability | Metrics + dashboards for the body | Prometheus + Grafana |

### 3.3 The complete tech stack (with one-line rationale)
| Layer | Choice | Why |
|---|---|---|
| Backend language | **Python 3.11+** | You know it; best GTFS + agent ecosystem; focus learning on systems/agents not syntax. |
| Web framework | **FastAPI** | Async (good for live connections + agents), auto API docs, great WebSocket support, pairs with Pydantic AI. |
| Database | **PostgreSQL** | Industry-standard relational DB; one DB serves relational, spatial, time-series, and vector needs. |
| Spatial | **PostGIS** | Standard spatial extension; real spatial queries + indexes. |
| Spatial index | **H3** | Fast hex aggregation; Uber-grade keyword. |
| Time-series | **TimescaleDB** | Efficient position history + retention. |
| Vector store | **pgvector** (in Neon) | Agent memory + RAG with no new infra; join vectors with PostGIS data. |
| Cache + queue + conv memory | **Redis** (Upstash) | Caching, Redis Streams pipeline, and conversation memory — one tool, several lessons. |
| Real-time | **WebSockets** (FastAPI) | Live map; fan-out. |
| Vector tiles | **Martin** / **pg_tileserv** | MVT straight from PostGIS. |
| Frontend | **Next.js + React** | The in-demand frontend stack; hosts the streaming chat + generative UI. |
| Map | **MapLibre GL JS** | Free, open-source vector-tile map the agent can draw on. |
| Agent copilot UI | **CopilotKit** (AG-UI) | In-app copilot: shared state, frontend actions (map fusion), live agent-state rendering; bridges to Python. |
| ML | **LightGBM** + pandas/scikit-learn | Right-sized regression; fast on CPU; interpretable. |
| Agent framework | **Pydantic AI** | Type-safe, model-agnostic (one-string switch), tools/memory/streaming/MCP/evals, FastAPI ergonomics. |
| LLM providers | **Gemini 2.5 Flash → Groq → Cerebras → OpenRouter** | Free tiers with function calling; fallback chain for a public app. |
| Agent tracing | **Langfuse** | Free tier (or self-host) tracing + evals for the agent. |
| Evals | **Pydantic Evals** (+ Langfuse datasets) | Golden set, LLM-as-judge, trajectory checks. |
| MCP | **FastMCP / Pydantic AI MCP** | Expose tools over the 2026 interop standard. |
| Containers | **Docker + docker-compose** | One-command stack; ship like real teams. |
| CI/CD | **GitHub Actions** | Lint, test, build, deploy on every push. |
| Observability | **Prometheus + Grafana** | Metrics + dashboards for the body. |
| Testing | **pytest** | Standard Python testing. |
| Deploy (data) | **Neon** (Postgres+PostGIS+Timescale+pgvector), **Upstash** (Redis) | Free managed tiers with all needed extensions. |
| Deploy (compute) | **DigitalOcean droplet** (GitHub Student $200) *or* Render/Koyeb free | Always-on host avoids cold starts that ruin a live agent demo. |
| Deploy (frontend) | **Cloudflare Pages** | Free static hosting, unlimited bandwidth. |
| Object storage | **Cloudflare R2** | Free 10 GB for history (Parquet) + model files. |

> **Optional stretch (résumé boosts), after it works:** rewrite the poller in **Go**; swap Redis Streams for **Kafka**; add **gRPC** between services; implement the Watchdog in **LangGraph**; run the stack on **k3s** (lightweight Kubernetes).

### 3.4 Repository layout (monorepo)
```
livetransit-copilot/
├── README.md                      # front door (write last, polish hard)
├── docker-compose.yml             # local stack: postgres, redis, api, workers, tiles, (grafana/prometheus)
├── .env.example                   # documents every env var (NO real secrets)
├── .gitignore                     # MUST ignore .env, __pycache__, *.pb, data dumps, model files, .next/
├── .github/workflows/ci.yml       # lint + test + build (+ deploy on main)
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint (REST + WS + agent routes)
│   │   ├── api/                   # REST + WebSocket handlers
│   │   ├── core/                  # config, db, logging, metrics
│   │   ├── ingest/                # poller + processor workers
│   │   ├── models/                # DB schema helpers
│   │   ├── ml/                    # features, train, predictor
│   │   ├── tiles/                 # tile config (if not standalone)
│   │   ├── agent/
│   │   │   ├── tools.py           # the 7 tool functions (call the body)
│   │   │   ├── copilot.py         # the ReAct agent (Pydantic AI)
│   │   │   ├── watchdog.py        # the background monitoring agent
│   │   │   ├── memory.py          # Redis conversation + pgvector long-term/vector
│   │   │   ├── rag.py             # chunk/embed/retrieve + corrective loop
│   │   │   ├── gateway.py         # provider routing + fallback + usage limits
│   │   │   └── guardrails.py      # text-to-PostGIS validation, output checks
│   │   ├── mcp/                   # MCP server exposing the tools
│   │   └── evals/                 # golden set + eval harness
│   └── tests/                     # pytest unit + integration
├── frontend/                      # Next.js + React + MapLibre + CopilotKit
│   ├── package.json
│   ├── app/                       # pages/routes
│   └── components/                # map, chat, generative-UI cards
├── db/
│   ├── migrations/                # versioned schema changes (incl. pgvector, timescale)
│   └── load_static_gtfs.py        # one-off schedule loader
├── ops/
│   ├── prometheus.yml
│   └── grafana/                   # dashboard JSON
└── docs/
    └── architecture.md            # diagram + decisions (link from README)
```

### 3.5 The data model (starter schema)
Static GTFS: `routes`, `stops(geom geometry(Point,4326))`, `trips`, `stop_times` (composite key `(trip_id, stop_sequence)`), `shapes(geom geometry(LineString,4326))`.

Live + history: `vehicle_positions(id, vehicle_id, trip_id, route_id, geom, bearing, h3_cell, recorded_at)` → a **Timescale hypertable** on `recorded_at`; `predictions` + `actuals` for ETA evaluation.

Agent layer: `conversations`/`messages` (or Redis) for short-term memory; `user_memory(user_id, key, value, embedding vector)` for long-term/vector memory; `rag_documents(id, source, chunk_text, embedding vector, metadata)` for the RAG library; `incidents(id, kind, route_id, summary, evidence, created_at)` for Watchdog reports; optional `agent_runs`/`tool_calls` mirrors (Langfuse also stores these).

Indexes to add and *measure*: GiST on `stops.geom` and `vehicle_positions.geom`; B-tree on `vehicle_positions.h3_cell`, `(trip_id)`, `recorded_at`; **HNSW** on the `embedding` columns (pgvector).

---

## PART 4 — Prerequisites, accounts & setup (do this before Phase 0)

> Do every install and signup *with Claude Code explaining each one first*. Don't paste keys anywhere public.

### 4.1 Local tools to install
- **Git** — version control.
- **Docker Desktop** (or Docker Engine) — runs the whole local stack (Postgres, Redis, API, workers, tiles) in containers so you don't install databases directly on your laptop. This is the big one.
- **Python 3.11+** — backend + agent (Docker also provides it; keep a local interpreter for tooling).
- **Node.js 20+** — required for the Next.js/React/CopilotKit frontend.
- **A code editor** — VS Code, which integrates with Claude Code.
- *(Run as Docker containers, nothing to install directly)* **Martin/pg_tileserv** (tiles), **Prometheus/Grafana** (observability), optionally **OpenTripPlanner** (trip routing) and **Langfuse** (if self-hosting).

> **4060 / 8 GB laptop note:** everything in development runs comfortably. Docker + Postgres + Redis are light; LightGBM trains on CPU in minutes; **the LLM is hosted, so no GPU is used for the agent.** The only caution is disk for data dumps — keep them out of the repo (4.5). OpenTripPlanner and self-hosted Langfuse are the only RAM-hungry optionals; prefer their hosted/free alternatives first and only self-host if quotas force it.

### 4.2 Accounts to create (all free) — infrastructure
1. **GitHub** + **GitHub Student Developer Pack** (apply with your college email on day one — approval can take time). Unlocks a **$200 DigitalOcean credit** (your always-on deploy host), a free domain, JetBrains IDEs, and more.
2. **Neon** — free managed Postgres with **PostGIS, TimescaleDB, and pgvector** extensions (≈0.5 GB storage, scale-to-zero, no card). One database covers spatial, time-series, *and* agent memory/RAG.
3. **Upstash** — free serverless **Redis** (caching, Redis Streams, conversation memory).
4. **Cloudflare** — free **Pages** (frontend hosting) and **R2** (10 GB object storage for history Parquet + model files).
5. *(Deploy target, choose at Phase J)* **DigitalOcean** (Student credit, recommended for always-on) or **Render**/**Koyeb** free tiers.

### 4.3 Accounts to create (all free) — LLM & agent providers
You need at least the first; add the others as fallback (the chain is what keeps a public agent alive).
1. **Google AI Studio (Gemini API)** — primary brain. Free key; **Gemini 2.5 Flash** supports function calling + structured outputs. *Primary model string in Pydantic AI.*
2. **Groq** — fast fallback. Free key; **Llama 3.3 70B**, OpenAI-compatible, tool calling.
3. **Cerebras** — second fallback. Free key; very fast Llama models, tool calling.
4. **OpenRouter** — breadth fallback. Free key; the `openrouter/free` router auto-selects tool-calling models (note: free request/day cap is much higher once you've ever added ≥ $10 — see Part 7).
5. **Langfuse** — agent tracing/evals. Free Hobby tier (cloud), or self-host via Docker.

> Put every key in `.env` (local) and the platform secret store (prod). Pydantic AI selects a provider by a single model string, so the **fallback order is config, not code** — and that one-string switch is your insurance against the frequent free-tier changes.

### 4.4 The data sources (all free/public)
- **MBTA (Boston)** — your starting city and the agent's core substrate. GTFS-RT protobuf needs **no key**: `https://cdn.mbta.com/realtime/{VehiclePositions,TripUpdates,Alerts}.pb` (JSON mirrors exist). The optional free **V3 API key** lifts limits from **20 req/min to 1,000 req/min** and gives richer queries (vehicles, predictions, alerts, routes, stops, shapes, crowding). Download the **static GTFS zip** once for the schedule. License: MassDOT Developers License Agreement (attribute it). *Fallback city:* NYC subway GTFS-RT (no key; use `nyct-gtfs`); NYC bus needs a free key.
- **Open-Meteo** — weather for delay reasoning. **No key**, generous non-commercial use.
- **OpenStreetMap via Overpass** — POIs for "get me to X" (free, no key, one query at a time). **Nominatim** geocoding (public instance: **max 1 request/second**, no heavy/commercial use) or **Photon** (free, autocomplete) to turn "the airport" into coordinates.
- **OpenRouteService** — isochrones (**500/day, 20/min**) and directions (**2,000/day, 40/min**) with a free HeiGIT key; self-hostable via Docker to remove quotas.
- **OpenTripPlanner** — self-host (Docker, Java) for true GTFS multimodal trip planning (transit + walk + bike) with no quotas — the most authentic routing tool; use only if you want real transit routing beyond ORS.
- **Historical data for the ML model** (so you don't self-collect for weeks): start collecting your own MBTA history via the running poller in Phase 5, and optionally supplement from public archives (Kaggle "New York City Bus Data"; the NYC bus-position S3 archive; the MDPI Astana 2025 bus-travel-time dataset).

### 4.5 Critical discipline: secrets and storage
- Add `.env`, the GTFS zip, data dumps, model files, and `.next/` to `.gitignore` **immediately**. Committing a secret or a large dump is a classic, costly mistake.
- The **real-time firehose grows fast** and will overflow the ~0.5 GB Postgres tier in days. Keep only **static GTFS + a rolling window** (e.g., last 24–72 h) in Postgres; offload older history to **Parquet on R2**; train from the offload. Pick **one city / one mode** (e.g., MBTA subway or one bus garage) to stay small.
- pgvector memory/RAG also consume storage — keep embeddings to what you need (chunk sensibly; don't embed the entire internet).

---

## PART 5 — The build, phase by phase

> **Each phase has:** *Goal* → *Learn first* (concepts to understand before coding) → *Steps* → *Done when* (verification) → *Pitfalls* → *Concept check* (explain it back) → *Kickoff prompt* (paste into Claude Code to start the phase).
>
> **The golden rule applies to every step of every phase: understand before you run** (Part 0). The kickoff prompts restate it so Claude Code stays in teaching mode.
>
> Build order: **backend body (Phases 0–9)** first, then **agentic brain (Phases A–J)**, where Phase J deploys the whole system live.

---

### Phase 0 — Foundations: repo, Docker, local database
**Goal:** A version-controlled repo and a one-command local stack (Postgres + PostGIS + Redis) in Docker, with MBTA static GTFS loaded and queryable.

**Learn first:** 2A.5 (DB/SQL), 2A.6 (PostGIS), 2A.15 (Docker/compose), 2A.16 (env vars), 2A.17 (git), 2A.22 (GTFS static).

**Steps:** create the GitHub repo, clone, add `.gitignore` (ignore `.env`, `__pycache__/`, `*.pb`, dumps, model files, `.next/`) and a stub README → write `docker-compose.yml` with a **PostGIS** image (`postgis/postgis`) + `redis`, with a named volume so data persists → create `.env.example` and a real git-ignored `.env` (`DATABASE_URL`, `REDIS_URL`) → `docker compose up`, connect, run `CREATE EXTENSION postgis;` and confirm `SELECT postgis_version();` → write `db/migrations/0001_init.sql` creating the static GTFS tables → download the MBTA static GTFS zip and write `db/load_static_gtfs.py` to parse CSVs and insert (build `stops.geom` from lon/lat as `geometry(Point,4326)`) → verify with SQL (counts; a `ST_DWithin` "stops near downtown" query).

**Done when:** `docker compose up` brings up Postgres+PostGIS+Redis; the schedule is loaded; a spatial query returns sensible stops; everything is committed and pushed.

**Pitfalls:** committing `.env` or the zip; forgetting `CREATE EXTENSION postgis`; lon/lat order (`ST_MakePoint(lon, lat)`); no Docker volume (data vanishes on restart).

**Concept check:** what Docker gives over installing Postgres directly; what PostGIS adds; why `.env` is git-ignored; what an SRID is and why 4326.

**Kickoff prompt:**
> We're on Phase 0 of LiveTransit Copilot. Goal: a git repo + docker-compose stack (Postgres+PostGIS and Redis) with MBTA static GTFS loaded and a working spatial query. Follow the Part 0 rules — explain each piece before building (docker-compose structure, the PostGIS image, named volumes, how the GTFS CSVs map to tables), propose the file layout first, and wait for my "go." After each file, tell me how to verify it.

---

### Phase 1 — First ingestion: poll, decode, store, expose
**Goal:** A poller that fetches MBTA VehiclePositions every ~10s, decodes the protobuf, stores positions, and a `GET /vehicles` FastAPI endpoint returning the latest positions.

**Learn first:** 2A.2 (HTTP), 2A.3 (REST), 2A.4 (protobuf), 2A.12 (poller as process), 2A.22 (GTFS-RT).

**Steps:** set up the Python backend (`fastapi`, `uvicorn`, `httpx`, `gtfs-realtime-bindings`, `asyncpg`/`psycopg`) → add a `vehicle_positions` table (no Timescale yet) → write the poller (`app/ingest/poller.py`): loop every ~10s, fetch the `.pb` URL, decode, extract `(vehicle_id, trip_id, route_id, lat, lon, bearing, timestamp)`, insert; survive fetch failures (log + retry next tick) → build `GET /vehicles` and `GET /health` → run poller+API via compose; watch rows accumulate; check `/vehicles`.

**Done when:** live vehicles are written continuously and `GET /vehicles` returns current positions that match the real MBTA map.

**Pitfalls:** not handling feed failures (it occasionally 500s — your loop must survive); blocking the async event loop with sync calls; duplicates every tick (fixed properly in Phase 2 — note it now); timezones (store everything UTC).

**Concept check:** why the poller is separate from the API; what protobuf is and why the feed uses it; what `GET /vehicles` does from request to response.

**Kickoff prompt:**
> Phase 1 of LiveTransit Copilot. Goal: a poller fetching+decoding MBTA VehiclePositions every ~10s into storage, plus `GET /vehicles`. Per Part 0, first explain how gtfs-realtime-bindings decodes the feed, the VehiclePositions structure, why poller and API are separate, and how async fetching works. Propose the files, wait for my go, and give me a verification step after each.

---

### Phase 2 — Streaming pipeline: decouple, dedupe, H3, spatial queries
**Goal:** A Redis Stream between poller and storage; the poller only publishes; a processor consumes, dedupes (idempotency), H3-tags, and writes. Add spatial queries + a GiST index and *measure* the speedup.

**Learn first:** 2A.7 (indexes), 2A.8 (H3), 2A.10 (Redis), 2A.11 (streams/idempotency/backpressure).

**Steps:** refactor the poller to **publish** to a Redis Stream (`XADD`) instead of writing the DB → write the processor (`XREADGROUP` with a consumer group): dedupe by `(vehicle_id, timestamp)`, compute the H3 cell, write the row, `XACK` → add a GiST index on `vehicle_positions.geom` and a B-tree on `h3_cell`; run a "within 500 m" query with `EXPLAIN ANALYZE` **before and after** and record the timing → add `GET /vehicles/near` (`ST_DWithin`) and `GET /vehicles/cell/{h3}` → add short-TTL Redis caching to a hot endpoint.

**Done when:** poller→stream→processor→DB works end to end; re-processing an item is harmless; spatial + H3 queries are correct; you can quote the index speedup.

**Pitfalls:** forgetting `XACK` (endless reprocessing); wrong H3 resolution (explain your choice); cache staleness (short TTL); skipping the consumer group (lose retry/scaling).

**Concept check:** what the stream buys vs direct writes; define idempotency + your dedupe key; what GiST does and what `EXPLAIN ANALYZE` showed; why hexagons.

**Kickoff prompt:**
> Phase 2 of LiveTransit Copilot. Goal: insert a Redis Stream between poller and a new processor; make processing idempotent; add H3 tagging; add a GiST index and spatial endpoints; add short-TTL caching. Per Part 0, first teach Redis Streams + consumer groups, idempotency and the dedupe key, GiST/R-tree indexes, and H3 resolutions, and show me EXPLAIN ANALYZE before/after. Propose the refactor and wait for my go.

---

### Phase 3 — Real-time frontend: WebSockets + a live map
**Goal:** A page with a MapLibre map where live vehicle dots move in real time via a WebSocket that fans out from a single upstream poll.

**Learn first:** 2A.1 (frontend/backend), 2A.13 (WebSockets/fan-out), 2A.14 (MapLibre basics).

**Steps:** add a WebSocket endpoint (`/ws/vehicles`), track connected clients, broadcast latest positions on update/timer (optionally accept a bounding box per client) → build a minimal frontend (MapLibre map + WebSocket client that updates dot markers) → smooth motion by interpolating between updates → add a click-popup (route + vehicle id).

> *Note:* this is the minimal map. In Phase C you'll replace/extend this with the full **Next.js + CopilotKit** frontend that fuses chat with the map. Keep Phase 3 simple — its job is to prove the live data + fan-out work.

**Done when:** real vehicles move live; two browser tabs both update from the same single upstream feed (proves fan-out).

**Pitfalls:** re-fetching per client (defeats the design); not pruning disconnected clients (leak); over-sending (throttle/diff); CORS between frontend and API.

**Concept check:** WebSocket vs normal HTTP; what fan-out is and why it scales; the path from "new position processed" to "dot moves."

**Kickoff prompt:**
> Phase 3 of LiveTransit Copilot. Goal: a MapLibre page with live dots driven by a WebSocket fan-out. Per Part 0, first teach WebSockets vs HTTP, how FastAPI manages WS connections, safe broadcast (handling disconnects), and minimal MapLibre. Build backend WS + frontend incrementally; after each step show me how to verify, including two tabs to prove fan-out. Wait for my go.

---

### Phase 4 — Vector tiles: render the real network
**Goal:** Serve routes and stops as vector tiles from PostGIS and render them as map layers under the live dots.

**Learn first:** 2A.14 (vector tiles / MVT / tile servers, fully).

**Steps:** run **Martin** or **pg_tileserv** as a Docker service pointed at PostGIS → add the tile source + layers to MapLibre (route `shapes` as colored lines using `route_color`; `stops` as circles) → make stops clickable (sets up Phase 6 + the agent's stop UI) → zoom-dependent styling (labels only when zoomed in).

**Done when:** the real network (routes + stops) renders as vector tiles with live dots over it, smooth on pan/zoom.

**Pitfalls:** sending raw geometry instead of tiles (slow/huge); SRID mismatches (tiles expect 3857 — the server reprojects, but understand it); over-styling.

**Concept check:** why you can't send the whole city's geometry; what a vector tile is and what the tile server does; 4326 vs 3857.

**Kickoff prompt:**
> Phase 4 of LiveTransit Copilot. Goal: serve routes/stops as vector tiles from PostGIS (Martin/pg_tileserv) and render them in MapLibre under the live dots. Per Part 0, first teach MVT, how a tile server generates tiles from PostGIS, 4326→3857 reprojection, and MapLibre sources/layers/styles. Set up the tile server, add layers one at a time, verify each. Wait for my go.

---

### Phase 5 — Time-series & history: store the past without drowning
**Goal:** Convert `vehicle_positions` into a TimescaleDB hypertable with retention + continuous aggregates, offload old data to R2, and derive actual-arrival labels for ML.

**Learn first:** 2A.9 (time-series/TimescaleDB), 4.5 (storage discipline).

**Steps:** enable TimescaleDB; convert `vehicle_positions` to a hypertable on `recorded_at` → add a retention policy (drop raw rows older than ~72 h) → before deletion, offload older positions to **Parquet on R2** → add a continuous aggregate (per-route/segment travel time per hour) → derive **actual arrival events** (vehicle reaches a stop) and join with the schedule to compute delays (your ML labels).

**Done when:** history accrues as a hypertable, old raw data is offloaded + pruned automatically, and you have a growing "actual arrivals with delays" table.

**Pitfalls:** letting raw positions fill the tier (retention + offload early); naive arrival detection (define "reached stop" = nearest-approach within a threshold); inconsistent UTC.

**Concept check:** what a hypertable is and why partition by time; what retention does and where offloaded data goes; turning positions into arrival labels.

**Kickoff prompt:**
> Phase 5 of LiveTransit Copilot. Goal: make vehicle_positions a Timescale hypertable with retention, offload old data to Parquet on R2, add a travel-time continuous aggregate, and derive arrival labels with delays. Per Part 0, first teach hypertables, retention, continuous aggregates, and a robust "reached stop" rule. Propose schema changes + the offload job; wait for my go.

---

### Phase 6 — The ML core: predict arrivals, measure error
**Goal:** A LightGBM arrival predictor served behind `GET /stops/{id}/arrivals`, with MAE vs schedule + historical-average baselines shown in the UI.

**Learn first:** 2A.21 (regression/features/splits/MAE/gradient boosting).

**Steps:** feature engineering (`app/ml/features.py`): per (trip, upcoming stop) — current delay, time-of-day, day-of-week, recent segment travel times (from the aggregate), stops remaining, optional weather; build a training table from the history archive → compute **baselines first** (schedule, historical average) and their MAE → train (`train.py`): **time-based** split (never random), LightGBM, evaluate MAE on a held-out period, save the model to R2 (not git) → serve (`predictor.py`): load at startup; compute features live; return ETAs → frontend: clicking a stop shows predicted arrivals + an accuracy panel (your MAE vs baselines vs agency).

**Done when:** clicking a stop shows your predictions; held-out MAE **beats the schedule baseline**; the comparison is visible.

**Pitfalls:** **data leakage** (random splits, or future-info features) — split by time, features only from data available at prediction time; no baseline; over-engineering the model; un-scripted retraining.

**Concept check:** why regression not classification; why split by time; what MAE is and why beat a baseline; three features and why each helps; what leakage is and how you avoided it.

**Kickoff prompt:**
> Phase 6 of LiveTransit Copilot. Goal: a LightGBM ETA predictor behind `GET /stops/{id}/arrivals` with MAE vs schedule and historical-average baselines. Per Part 0, first teach regression vs classification, time-based splitting and why random leaks, spatiotemporal feature engineering, MAE, and beating baselines. Build features → baselines → train → evaluate → serve, explaining and verifying each. Wait for my go.

---

### Phase 7 — Observability: prove the body works
**Goal:** Instrument all body services with metrics, scrape with Prometheus, and build a Grafana dashboard (ingestion lag, feed freshness, events/sec, WS clients, p50/p99 latency, cache hit rate, prediction MAE).

**Learn first:** 2A.20 (logs/metrics/Prometheus/Grafana).

**Steps:** add structured logging everywhere → expose Prometheus metrics (counters: positions processed; gauges: feed age, WS clients; histograms: latency) → run Prometheus + Grafana (Docker), connect them → build the dashboard → add health checks + a basic alert ("feed age > 60s"). Screenshot it for the README.

**Done when:** a Grafana dashboard shows the body's vital signs live and you can explain what healthy looks like.

**Pitfalls:** logging secrets; high metric label cardinality (don't label by vehicle_id); an unreadable dashboard.

**Concept check:** logs vs metrics; counters vs gauges vs histograms; what p99 means and why care over the average.

**Kickoff prompt:**
> Phase 7 of LiveTransit Copilot. Goal: Prometheus metrics + structured logs across body services, Prometheus + Grafana in Docker, and a dashboard. Per Part 0, first teach logs vs metrics, counter/gauge/histogram, percentiles, and label-cardinality pitfalls. Add metrics service by service, verifying each appears in Prometheus before the dashboard. Wait for my go.

---

### Phase 8 — Testing: change code without fear
**Goal:** A pytest suite over the logic that matters — idempotency/dedupe, arrival detection, feature construction, the API contract — running locally and in CI.

**Learn first:** 2A.19 (the testing pyramid).

**Steps:** unit tests for pure logic (dedupe key, H3 tagging, feature builders, baseline math) → integration tests for the API against a Dockerized **test database** with fixtures → a couple of end-to-end checks (feed a recorded sample `.pb` through poller→processor→DB) → add fixtures (a saved `.pb`, a tiny GTFS subset) so tests don't hit the network.

**Done when:** `pytest` passes locally; risky logic is covered; you can refactor and trust the suite.

**Pitfalls:** testing trivial getters; network-dependent (flaky) tests; no test-DB isolation.

**Concept check:** unit vs integration vs e2e; what's most worth testing here and why; why fixtures over the live feed.

**Kickoff prompt:**
> Phase 8 of LiveTransit Copilot. Goal: a pytest suite for dedupe/idempotency, arrival detection, feature building, and the API contract, with a Dockerized test DB and recorded fixtures. Per Part 0, first teach the testing pyramid, what's worth testing here, and test-DB isolation. Write tests one module at a time, explaining each assertion. Wait for my go.

---

### Phase 9 — CI/CD: automate quality and shipping
**Goal:** A GitHub Actions pipeline that lints, runs tests against a service database, builds the Docker image, and (on main) deploys.

**Learn first:** 2A.18 (CI/CD / GitHub Actions).

**Steps:** add `ci.yml`: checkout → setup Python → install → lint (ruff/black) → pytest (with a Postgres **service container**) → build the Docker image → add branch protection (main requires green CI) → add a deploy job on main (build/push image; trigger the host to pull) → store all secrets in **GitHub Actions secrets**.

**Done when:** every push auto-runs lint+tests; a red build blocks merge; merging to main deploys.

**Pitfalls:** secrets committed or echoed; CI that skips DB-dependent tests; flaky CI from network calls (use fixtures).

**Concept check:** what CI and CD each mean; what your workflow does stage by stage; why CI needs its own database service.

**Kickoff prompt:**
> Phase 9 of LiveTransit Copilot. Goal: a GitHub Actions pipeline (lint → pytest with a Postgres service container → build image → deploy on main). Per Part 0, first teach workflows/jobs/steps, service containers as a test DB, and Actions secrets. Build it incrementally, explaining each YAML block. Wait for my go.

---

### Phase A — The first agent: tools + LLM gateway + a ReAct loop
**Goal:** A single Pydantic AI agent that, given an English question, calls three real read-only tools and answers — proving the agent loop end to end.

**Learn first:** 2B.1 (program vs chatbot vs agent), 2B.2 (ReAct loop), 2B.3 (tools/function calling), 2B.5 (Pydantic AI), 2B.13 (hosted LLM + free tiers).

**Steps:** create the Google AI Studio (Gemini) key; add it to `.env` → add the LLM gateway (`app/agent/gateway.py`): configure Pydantic AI to use Gemini 2.5 Flash, with a usage limit on tool-call depth → write three tools (`app/agent/tools.py`) as plain async functions over the body: `get_vehicle_positions(route)`, `predict_eta(stop_id)`, `get_service_alerts(route)`; decorate them with `@agent.tool` → build the agent (`app/agent/copilot.py`) with a clear system prompt describing its job and tools → add `POST /agent/ask` that runs the agent on a question and returns the final text → test with real questions ("Where are the Red Line trains?", "When's the next train at Park Street?").

**Done when:** a real question triggers the right tool call(s) against live data and returns a truthful answer; you can see (in logs) which tools were called.

**Pitfalls:** vague tool docstrings (the model picks tools from them — be precise); no depth cap (an agent can loop and burn quota); blocking calls inside async tools; exposing write/dangerous tools (keep Phase A read-only).

**Concept check:** draw the ReAct loop; what a tool is and how function calling works; what happens from question → tool call → observation → answer; why the LLM is hosted.

**Kickoff prompt:**
> Phase A of LiveTransit Copilot — our first agent. Goal: a Pydantic AI ReAct agent with three read-only tools over the live data, behind `POST /agent/ask`. Per Part 0, first teach the agent loop, tool/function calling, how Pydantic AI turns a function into a tool, and how the hosted Gemini model is wired in. Build the gateway, then one tool at a time, then the agent; after each, show me how to verify which tool was called. Wait for my go.

---

### Phase B — Structured outputs + streaming the reasoning
**Goal:** The agent returns typed, validated objects (`TripPlan`, `IncidentReport`, `ArrivalAnswer`) and streams its tokens *and* tool steps to a basic chat UI.

**Learn first:** 2B.4 (structured outputs), 2B.10 (streaming).

**Steps:** define Pydantic output schemas for the main answer types → set the agent's `output_type` so results are validated (and auto-retried if malformed) → switch the endpoint to **stream** (SSE): emit text deltas and tool-step events ("calling predict_eta…") → build a minimal streaming chat box (you'll upgrade it in Phase C) that shows the live trace + final structured card.

**Done when:** answers come back as validated objects, and the UI shows the agent's steps appearing live, ending in a structured result.

**Pitfalls:** over-broad schemas (keep them tight); not handling validation-retry; buffering instead of streaming (kills the effect); forgetting to stream tool events, not just text.

**Concept check:** why structured outputs matter and what happens on malformed output; what's streamed and why the tool-step trace matters.

**Kickoff prompt:**
> Phase B of LiveTransit Copilot. Goal: typed/validated agent outputs (TripPlan, IncidentReport, ArrivalAnswer) and streaming of tokens + tool steps to a basic chat UI. Per Part 0, first teach structured outputs + validation/retry and how streaming works (text deltas and tool-step events over SSE). Define schemas, wire output_type, switch to streaming, build a minimal trace UI — verifying each. Wait for my go.

---

### Phase C — The real frontend: Next.js + CopilotKit + map fusion
**Goal:** A polished Next.js + React frontend where chat sits beside the live MapLibre map and the agent *manipulates the map* (drops pins, draws routes, shades isochrones) via generative UI.

**Learn first:** 2B.15 (generative UI / map fusion / CopilotKit), 2A.14 (MapLibre recap).

**Steps:** scaffold the Next.js app (Node 20+); bring over the MapLibre map + live WebSocket dots from Phase 3 → install **CopilotKit**; connect it to the Python agent backend (AG-UI over an SSE endpoint) → expose map/app state to the agent with `useCopilotReadable`; define frontend actions with `useCopilotAction` (`drawRoute`, `dropPin`, `highlightVehicles`, `showIsochrone`) → render live agent state with `useCoAgentStateRender` → build generative-UI cards for `TripPlan` and `IncidentReport` with citations → polish the layout (chat + map side by side, the streaming trace, clean styling).

**Done when:** you ask a trip question and watch the agent draw the route and render a trip-plan card; you ask about delays and watch it highlight vehicles — all streamed.

**Pitfalls:** trying to run agent logic in the browser (keep it in Python; the frontend triggers actions); CORS/origin between Next.js and the API; the map and agent state drifting out of sync; over-animating.

**Concept check:** what generative UI and map fusion are; how CopilotKit lets the agent read app state and trigger frontend actions; where the agent actually runs.

**Kickoff prompt:**
> Phase C of LiveTransit Copilot. Goal: a Next.js + React + MapLibre + CopilotKit frontend where the agent draws on the map (routes, pins, isochrones, highlights) via generative UI, with chat beside the map. Per Part 0, first teach generative UI, map fusion, and how CopilotKit's readable/action/state hooks bridge the React frontend to my Python agent. Scaffold, connect, then add one map action at a time, verifying each live. Wait for my go.

---

### Phase D — Memory: conversation + long-term + vector
**Goal:** The agent remembers within a chat (Redis) and across sessions (pgvector) — user home/work stops, preferences, and similar past situations.

**Learn first:** 2B.6 (three memories + embeddings + pgvector).

**Steps:** enable **pgvector** in Neon; add `user_memory` + (optional) `conversations`/`messages` tables with `embedding vector` columns and an **HNSW** index → wire short-term memory: load recent conversation turns from Redis into the agent's context → wire long-term memory: a tool/step that stores and retrieves user facts (embed the fact, store in pgvector; retrieve by similarity) → add vector recall of similar past incidents/queries → confirm the agent uses remembered preferences (e.g., fewer transfers) without being re-told.

**Done when:** the agent recalls earlier turns, remembers your home stop across sessions, and surfaces similar past situations.

**Pitfalls:** unbounded memory growth (cap/prune; embed sensibly); storing secrets in memory; confusing the three tiers; no HNSW index (slow similarity search).

**Concept check:** name the three memory types and where each lives; what an embedding is and how similarity search works; why pgvector lives in the same database.

**Kickoff prompt:**
> Phase D of LiveTransit Copilot. Goal: conversation memory (Redis) + long-term/vector memory (pgvector) so the agent remembers turns, preferences, and similar past situations. Per Part 0, first teach the three memory tiers, embeddings, and pgvector similarity search with HNSW. Enable pgvector, add the tables/indexes, then wire each memory tier, verifying recall at each step. Wait for my go.

---

### Phase E — Agentic RAG over alerts & policy docs
**Goal:** The agent looks up service alerts and agency policy docs in a pgvector library, *checks* whether what it retrieved is relevant, and re-queries if not (corrective RAG) — answering "why is this line disrupted?" with citations.

**Learn first:** 2B.7 (RAG vs agentic RAG / CRAG), 2B.6 (embeddings/pgvector recap).

**Steps:** build the document library: ingest live MBTA alerts + GTFS reference docs + agency policy pages; chunk, embed, store in `rag_documents` (pgvector) → add a `retrieve(query)` tool that returns top-k relevant chunks → add the **corrective** step: score retrieved-chunk relevance; if below a threshold, rephrase/re-query or hit a different source before answering → make the agent cite the chunks it used → keep the alert ingestion fresh (re-embed on update).

**Done when:** "why is the Red Line delayed?" returns a grounded, cited answer; when the first retrieval is weak, you can see the agent re-query before answering.

**Pitfalls:** stuffing too much into context; no relevance check (that's the whole point of *agentic* RAG); **prompt injection** via alert text (treat retrieved content as data, not commands — see 2B.16); stale embeddings.

**Concept check:** classic vs agentic (corrective) RAG; how chunk→embed→retrieve works; when and why the agent re-queries; how you defend against injection in retrieved text.

**Kickoff prompt:**
> Phase E of LiveTransit Copilot. Goal: agentic (corrective) RAG over service alerts + policy docs in pgvector, with a relevance check that triggers a re-query, and citations. Per Part 0, first teach RAG vs agentic RAG, chunking/embedding/retrieval, the corrective loop, and prompt-injection safety on retrieved text. Build ingestion → retrieve tool → corrective step → citations, verifying each. Wait for my go.

---

### Phase F — The Network Watchdog: multi-agent orchestration
**Goal:** A second, autonomous agent that continuously monitors the live feed, detects anomalies (bunching, delays, service gaps), investigates via tools, and writes incident reports — with the Copilot able to delegate to it (supervisor/worker).

**Learn first:** 2B.8 (multi-agent / supervisor-worker / other patterns).

**Steps:** write the Watchdog (`app/agent/watchdog.py`): on a schedule, scan recent positions for anomalies (define bunching/gap/delay rules), and for each, call tools (+ weather) to investigate and produce a structured `IncidentReport` → store reports in `incidents`; surface them in the UI (a live incidents panel) and optionally as alerts → add supervisor delegation: the Copilot can ask the Watchdog to investigate a specific route on demand → keep token use bounded (the Watchdog runs often — cap its work).

**Done when:** the Watchdog posts real incident reports as anomalies occur, and the Copilot can delegate an investigation to it.

**Pitfalls:** a chatty Watchdog burning quota (rate-limit it, cap depth); vague anomaly rules (false positives); the two agents stepping on shared state; over-architecting into many agents (two is enough to demonstrate the pattern).

**Concept check:** what supervisor/worker is, and how it differs from planner-executor, reflection, and evaluator-optimizer; how the two agents share tools and state safely.

**Kickoff prompt:**
> Phase F of LiveTransit Copilot. Goal: a background "Network Watchdog" agent that detects transit anomalies, investigates via tools, and writes incident reports, with the Copilot able to delegate to it (supervisor/worker). Per Part 0, first teach multi-agent orchestration patterns and contrast them, and how to bound the Watchdog's token use. Build anomaly rules → investigation → reports → delegation, verifying each. Wait for my go.

---

### Phase G — Evals: prove the agent is actually good
**Goal:** A repeatable eval harness — a golden set plus LLM-as-judge and trajectory/tool-correctness checks — run on every change.

**Learn first:** 2B.11 (evals / trajectory / LLM-as-judge).

**Steps:** build a **golden set** (~50–100 hand-crafted question→expected-behavior cases across trip planning, delays, spatial queries, memory) → set up **Pydantic Evals** (and/or Langfuse datasets) → add **LLM-as-judge** scoring with explicit rubrics for answer quality → add **trajectory/tool-correctness** checks (did it call the right tools, in a sensible order, without pointless loops?) → run the suite and record a baseline score; wire it into CI (or a manual command) so regressions are caught.

**Done when:** you can run the evals and get scores for answer quality *and* trajectory; a deliberately broken change makes a score drop.

**Pitfalls:** judging only the final answer (misses wasted tool calls); a tiny/biased golden set; non-deterministic flakiness (set sensible tolerances); under-investing here (good cases take time — it's worth it).

**Concept check:** what an eval is and why it's hard; trajectory eval vs final-answer eval; what LLM-as-judge is and its limits.

**Kickoff prompt:**
> Phase G of LiveTransit Copilot. Goal: an eval harness — golden set + LLM-as-judge (rubric) + trajectory/tool-correctness checks — runnable on demand and in CI. Per Part 0, first teach agent evals, the difference between trajectory and final-answer evals, and LLM-as-judge with its limits. Help me build a small high-quality golden set first, then the scorers, verifying on a known-good and a deliberately-broken case. Wait for my go.

---

### Phase H — Tracing + cost/rate-limit engineering
**Goal:** Full agent observability via Langfuse, plus the engineering that keeps a *public* free-tier agent alive — caching, per-user rate limiting, provider fallback, and a request queue.

**Learn first:** 2B.12 (tracing / Langfuse), 2B.14 (cost & rate-limit engineering), 2B.13 (provider fallback).

**Steps:** create a Langfuse project (cloud free or self-host); instrument the agent so every model call, tool call, and retrieval is traced as nested observations → add **response/tool caching** (reuse recent identical results) → add **per-IP/user rate limiting** → implement the **fallback chain** (Gemini → Groq → Cerebras → OpenRouter) as config in the gateway → add a **request queue** for bursts; cap tool-call depth via Pydantic AI usage limits → watch a real trace and use it to find/fix one inefficiency (e.g., a redundant tool call).

**Done when:** every agent run is fully traced in Langfuse; the agent stays responsive under repeated use; exhausting one provider transparently fails over to the next.

**Pitfalls:** logging secrets/PII into traces; caching too aggressively (stale answers); fallback that loses tool context on switch; no depth cap (loops drain quota).

**Concept check:** logs/metrics vs agent tracing; what you cache and the staleness trade-off; how the fallback chain works and why it's config not code; why a public agent needs rate limiting.

**Kickoff prompt:**
> Phase H of LiveTransit Copilot. Goal: Langfuse tracing of every agent step, plus caching, per-user rate limiting, the Gemini→Groq→Cerebras→OpenRouter fallback chain, and a request queue. Per Part 0, first teach agent tracing, what to cache (and staleness), how provider fallback works as config, and why public agents need rate limiting. Instrument tracing first, then add each protection, verifying with a real trace and a forced-failover test. Wait for my go.

---

### Phase I — MCP server: expose your tools to the world
**Goal:** An MCP server exposing the LiveTransit tools so any MCP-compatible app (Claude Desktop, Cursor) can drive your transit system.

**Learn first:** 2B.9 (MCP).

**Steps:** stand up an MCP server (FastMCP or Pydantic AI's MCP support) over **Streamable HTTP**, registering the existing tools as MCP **Tools** (and optionally exposing read data as **Resources** and canned **Prompts**) → reuse the same guardrails (read-only, allow-lists) → connect an MCP host (e.g., Claude Desktop) and drive a tool from it → document the connection in the README (this is a memorable demo).

**Done when:** an external MCP host can list and call your tools and get live transit answers.

**Pitfalls:** duplicating tool logic (reuse the same functions); dropping guardrails on the MCP path; transport/auth misconfig.

**Concept check:** what MCP is and what problem it solves; Tools vs Resources vs Prompts; why exposing tools via a standard beats custom integrations.

**Kickoff prompt:**
> Phase I of LiveTransit Copilot. Goal: an MCP server (Streamable HTTP) exposing my existing tools so Claude Desktop/Cursor can use my transit system, reusing the same guardrails. Per Part 0, first teach MCP (Tools/Resources/Prompts, JSON-RPC, the transport) and why it matters. Stand up the server, register tools, connect an MCP host, and verify a real tool call end to end. Wait for my go.

---

### Phase J — Deploy the whole system, live
**Goal:** The entire body + brain running publicly: data on Neon, Redis on Upstash, compute on an always-on host, frontend on Cloudflare Pages, the agent reachable with the provider fallback in place, tracing on, and a real URL in the README.

**Learn first:** 4.2–4.3 (free tiers + providers), 2A.16 (production secrets), 2B.14 (rate-limit engineering recap).

**Steps:** **database** — Neon project; enable PostGIS + TimescaleDB + pgvector; run migrations; load static GTFS → **Redis** — Upstash; wire `REDIS_URL` → **compute** — provision the **DigitalOcean droplet** (Student credit) or a Render/Koyeb service; install Docker; bring up API + poller + processor + tiles + agent (+ MCP) with prod secrets via the host's secret store → **frontend** — build and deploy the Next.js app to Cloudflare Pages; point it at the public API/WS/agent URLs; set CORS/allowed origins → **history offload + retention** running in prod (R2) → **observability** — Prometheus+Grafana (body) and Langfuse (agent) reachable; link both from the README → **LLM keys** — set all provider keys as prod secrets; confirm the fallback chain works → **uptime** — restart-on-failure on the droplet (or an uptime pinger for sleeping free tiers) → **domain (optional)** — use your free Student-Pack domain with HTTPS.

**Done when:** a stranger can open the URL, watch live vehicles, chat with the Copilot, see it draw on the map and cite alerts, click a stop for predictions, and read live Watchdog incidents — and (via README links) see the metrics dashboard and an agent trace.

**Pitfalls:** secrets in the repo/compose (use the host's secret store); CORS misconfig; storage overflow in prod (retention/offload must be live); a sleeping free tier killing the demo (use the droplet or a pinger); no HTTPS; the agent's quota exhausted with no fallback (verify the chain).

**Concept check:** where each piece runs in production and why; how secrets reach the app without being in git; what keeps production storage bounded; how the agent survives free-tier limits.

**Kickoff prompt:**
> Phase J of LiveTransit Copilot — full deployment. Goal: deploy the whole system (Neon, Upstash, a DigitalOcean droplet for API+workers+tiles+agent+MCP, Cloudflare Pages for the Next.js frontend), with secrets handled properly, the R2 offload running, the provider fallback verified, and tracing on. Per Part 0, first teach how production secrets/config differ from local, running a Docker stack on a droplet, and wiring the frontend origin to the API with correct CORS. Walk me through each platform step, verifying connectivity at each stage. Wait for my go.

---

### 5.x Suggested timeline (flexible — understanding beats speed)
- **Weeks 1–2:** Phases 0–3 (foundations → streaming → live map). *Threshold: dots move on a local map via fan-out.*
- **Week 3:** Phases 4–5 (tiles → history). *Threshold: real network rendered; history within budget.*
- **Week 4:** Phase 6 (ML). *Threshold: held-out MAE beats the schedule baseline.*
- **Week 5:** Phases A–B (first agent → structured + streaming). *Threshold: a real question drives real tools and streams its steps.*
- **Week 6:** Phase C (Next.js + CopilotKit + map fusion). *Threshold: the agent draws your route on the map.*
- **Week 7:** Phases D–E (memory → agentic RAG). *Threshold: it remembers you and cites alerts.*
- **Week 8:** Phases F–G (Watchdog → evals). *Threshold: live incidents + an eval score.*
- **Week 9:** Phases H–I (tracing/cost → MCP). *Threshold: full traces, fallback works, an MCP host drives a tool.*
- **Week 10:** Phases 7–9 + J (observability, testing, CI/CD if not already, then deploy) + README/résumé polish. *Threshold: a stranger can use the public URL.*

> Fold backend Phases 7–9 (observability, testing, CI/CD) in wherever they fit best for you — many people add tests and CI earlier and observability before deploy. The order above front-loads the visible, motivating wins.

---

## PART 6 — Making it presentable

A finished system nobody can grasp in 30 seconds is wasted. This converts the work into the artifacts recruiters and interviewers actually look at.

### 6.1 The README (your front door)
In order: (1) one-line hook + **live link** + an animated GIF of the agent drawing a route on the live map; (2) what it does (3–4 plain bullets, both layers); (3) the **architecture diagram** (the Part 3 diagram as an image) + a short data-flow description; (4) tech stack grouped by layer; (5) **key results/metrics** (events/sec, p99 latency, cache hit rate, **prediction MAE vs baseline**, agent eval scores, fallback uptime); (6) run-it-locally (`docker compose up`, then `npm run dev` for the frontend); (7) "what I learned / design decisions" (link to `docs/architecture.md`); (8) license + MBTA/MassDOT attribution.

### 6.2 Capture these numbers as you build (`METRICS.md`)
Body: ingestion throughput (positions/sec; vehicles tracked); spatial-query speedup from indexing (the `EXPLAIN ANALYZE` before/after); API p50/p99 latency; cache hit ratio; concurrent WebSocket clients; prediction MAE (s) vs schedule and historical-average baselines; storage bounded (e.g., "raw positions capped at 72 h via retention + R2 offload"). Brain: number of tools; eval scores (answer-quality + trajectory); agent p95 latency; tokens/cost per query (from Langfuse); fallback behavior ("survives Gemini quota exhaustion via Groq"); RAG citation rate.

### 6.3 Résumé bullets (templates — fill with your real numbers)
- "Built a real-time transit platform ingesting **GTFS-Realtime** protobuf (~N positions/sec) through a **Redis Streams** pipeline with idempotent at-least-once processing into **PostgreSQL/PostGIS**; cut nearest-vehicle query latency from **X ms to Y ms** via **GiST** + **H3** indexing."
- "Served the network as **vector tiles** to a **MapLibre** frontend with single-poll **WebSocket** fan-out to N+ concurrent clients; trained a **LightGBM** ETA predictor (MAE **Z s**, beating schedule by **P%**) on **TimescaleDB** history with time-based splits to prevent leakage."
- "Built a production **agentic AI copilot**: a **Pydantic AI** ReAct agent with 7 tool-calling functions over live geospatial data, **pgvector** three-tier memory, **corrective agentic RAG** over service alerts/policy docs, a supervisor/worker **'Network Watchdog'** agent, an **MCP** tool server, **Langfuse** tracing, and an **LLM-as-judge + trajectory** eval harness."
- "Streamed agent reasoning to a **Next.js/CopilotKit** generative UI that draws routes/isochrones on the map; deployed live on free tiers with a **Gemini→Groq→Cerebras→OpenRouter** fallback chain, caching, and per-user rate limiting; containerized with **Docker**, automated via **GitHub Actions**, observed with **Prometheus/Grafana**."

### 6.4 Interview stories (rehearse 5)
1. **Decoupling** — the poller wrote straight to the DB and dropped data under load; a Redis Stream decoupled fetch from process (backpressure).
2. **Indexing** — nearest-vehicle queries scanned every row; a GiST index switched the plan from sequential to index scan, X→Y ms.
3. **Leakage** — a random train/test split made the ETA model look great by peeking at the future; a time-based split gave an honest MAE that still beat the baseline.
4. **Rate-limit engineering** — a *public* agent kept hitting free-tier caps; a provider-fallback chain + caching + per-user limits + a depth cap kept it alive (Pydantic AI's one-string switch made fallback config, not code).
5. **Trajectory eval** — final-answer scoring looked fine, but a trajectory eval caught the agent making redundant tool calls; fixing it cut tokens per query.

### 6.5 The demo script (the wow path)
Open the live map (dots moving) → ask the Copilot "fastest way from Kendall to the airport, and is the Red Line OK?" → watch it stream tool steps, draw the route, highlight the delayed segment, and answer with a cited reason → click a stop to show predicted vs actual arrivals → open the live Watchdog incidents panel → (finale) open Claude Desktop and drive a tool through **MCP** → link the Grafana dashboard and a Langfuse trace.

### 6.6 GitHub polish
Clean commit history (phases map to PRs); repo topics (`postgis`, `redis`, `fastapi`, `gtfs`, `geospatial`, `websockets`, `timescaledb`, `agentic-ai`, `pydantic-ai`, `mcp`, `rag`, `langfuse`); a pinned repo + profile README linking the live demo; no secrets or large binaries in history.

---

## PART 7 — Reference

### 7.1 Glossary (fast definitions)
**Backend terms:** *API* — a contract for requesting data. *Backpressure* — a queue absorbing bursts so a slow consumer doesn't lose data. *CI/CD* — automated test/deploy on every change. *Container* — an app packaged to run identically anywhere. *Continuous aggregate* — an auto-updating rollup (Timescale). *Fan-out* — one source update delivered to many clients from one fetch. *GiST index* — a spatial index for fast "near me." *GTFS / GTFS-RT* — the static schedule / real-time feed standard. *H3* — hexagonal global grid for fast spatial bucketing. *Hypertable* — a time-partitioned table (Timescale). *Idempotency* — re-processing an item causes no extra effect. *MAE* — average error in seconds. *MVT / vector tile* — compact per-area map geometry. *Protobuf* — compact binary format. *REST* — an HTTP API style over resources. *Retention policy* — auto-deletion of old data. *SRID 4326 / 3857* — GPS lat-long / web-map projection. *TTL* — cache expiry. *WebSocket* — a persistent server→client push connection.

**Agentic terms:** *Agent* — an LLM plus tools plus the autonomy to choose them. *ReAct loop* — reason → act → observe → repeat. *Tool / function calling* — the model requests a real function; your code runs it. *Structured output* — a validated, typed result (not free text). *Embedding* — text turned into meaning-numbers. *Vector store / pgvector* — stores embeddings, finds the closest fast. *RAG* — retrieve relevant docs, then answer. *Agentic / corrective RAG* — retrieval inside the reasoning loop, re-querying if results are weak. *Supervisor/worker* — one agent delegates to a specialist. *MCP* — an open standard ("USB-C for AI tools") to expose tools to any AI app. *Eval* — a repeatable test of agent quality. *Trajectory eval* — checks the path (tools, order), not just the answer. *LLM-as-judge* — a model scores outputs by a rubric. *Tracing* — a replayable record of every agent step. *Generative UI* — agent-generated interface pieces. *Map fusion* — the agent acting on the map. *Guardrails* — validation/limits that keep tool use safe. *Prompt injection* — malicious instructions hidden in retrieved text.

### 7.2 Command cheat sheet
```bash
# Docker
docker compose up -d            # start the stack
docker compose logs -f api      # follow a service's logs
docker compose down             # stop (add -v to wipe volumes)
docker compose exec postgres psql -U postgres   # DB shell

# Git everyday loop
git checkout -b phase-A-first-agent
git add -p && git commit -m "Add ReAct agent with 3 read-only tools"
git push -u origin phase-A-first-agent   # then open a PR

# Postgres / PostGIS / pgvector sanity
SELECT postgis_version();
SELECT extname FROM pg_extension;        -- confirm postgis, timescaledb, vector
EXPLAIN ANALYZE SELECT * FROM vehicle_positions
  WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(-71.06,42.36),4326), 0.005);

# Python / frontend / tests
pytest -q                       # backend tests
ruff check . && black .         # lint + format
npm run dev                     # Next.js frontend (in frontend/)
```

### 7.3 Free-tier limits & gotchas — infrastructure (verify at signup)
| Service | Free tier (approx., early–mid 2026) | Gotcha |
|---|---|---|
| **Neon** (Postgres) | ~0.5 GB, ~100 compute-hrs/mo, scale-to-zero; PostGIS/Timescale/pgvector | Limit overrun **suspends** compute; mind storage. |
| **Supabase** (alt) | ~500 MB, PostGIS, pgvector, Realtime | **Pauses after 7 days** inactivity. |
| **Upstash** (Redis) | ~256 MB, ~500K commands/mo | Command budget — don't poll wastefully. |
| **Cloudflare Pages** | Unlimited static bandwidth | Frontend only. |
| **Cloudflare R2** | 10 GB free | History Parquet + model files. |
| **Render** (compute) | Free web service, **spins down after 15 min idle**; free Postgres **expires in 30 days** | Cold starts ruin live demos; use Neon for DB. |
| **Koyeb** (compute) | Free instance, scale-to-zero | Signups sometimes limited; verify. |
| **DigitalOcean** (Student) | **$200 credit / 1 yr** | Best always-on host; set a budget alert. |
| **Railway / Fly.io** | **No longer truly free** | Avoid for "fully free." |
| **Langfuse** (tracing) | Hobby: ~50K units/mo, 30-day retention | Self-host via Docker if exceeded. |

> **Always-on demo tip:** put always-running pieces (API, poller, processor, tiles, **agent**, MCP) on the **DigitalOcean droplet** so the live agent never cold-starts. DB on Neon, Redis on Upstash, frontend on Cloudflare Pages.

### 7.4 Free-tier LLM providers & the fallback chain (verify at signup)
| Provider | Model | Free limits (approx., early–mid 2026) | Notes |
|---|---|---|---|
| **Google Gemini** (primary) | 2.5 Flash | **10 RPM / 250 requests-per-day / 250K TPM** | Function calling + structured outputs; **Dec 2025 free quotas cut 50–80%**, Pro now effectively paid — Flash/Flash-Lite are the free workhorses. |
| **Groq** (fallback 1) | Llama 3.3 70B | **30 RPM / 1,000 RPD / ~100K tokens-per-day** | Very fast; OpenAI-compatible; tool calling; the **token/day** cap binds first. |
| **Cerebras** (fallback 2) | Llama models | ~30 RPM + a daily token budget | World-record speed; tool calling; confirm exact daily token cap. |
| **OpenRouter** (fallback 3) | `openrouter/free` | **20 RPM / 50 RPD under $10 lifetime credit; 1,000 RPD once ≥ $10 ever added** | Auto-selects tool-calling models; best breadth/fallback; free models rotate. |

**Why a chain:** an agent loop can make 40+ model calls for a 10-step task, so a *public* app exhausts any single free tier fast. Design around the smallest caps; mitigate with caching, per-user rate limiting, prompt caching, capped tool-call depth, and a request queue. **Pydantic AI selects a provider by one model string, so the fallback order is configuration — change it freely as free tiers shift.**

### 7.5 Troubleshooting
- **`CREATE EXTENSION postgis/vector/timescaledb` fails** → not on an enabled image/instance; use `postgis/postgis` locally; enable extensions in Neon's dashboard.
- **Spatial query wrong/empty** → lon/lat order (`ST_MakePoint(lon, lat)`); confirm SRID 4326.
- **Poller dies when the feed is down** → wrap fetch in try/except, log, continue next tick.
- **Duplicate rows every tick** → implement the Phase 2 dedupe key.
- **Live map not updating** → CORS/origins, correct `ws/wss` URL, prune disconnected clients.
- **Storage filling fast** → retention + R2 offload must be active; one city/mode; shorter window.
- **Agent gives weird/empty answers** → open the **Langfuse trace**; check tool docstrings, the system prompt, and whether a tool errored silently.
- **Agent "hangs" or loops** → cap tool-call depth (usage limits); check for a tool that always returns "need more info."
- **Quota errors in the demo** → the fallback chain isn't wired or all providers are exhausted; verify the chain and add caching/limits.
- **text-to-PostGIS does something scary** → it must run under a read-only role with allow-listed tables and a statement timeout; never interpolate model text into SQL unchecked.
- **CI green locally, red in Actions** → tests depend on network/local state; use fixtures + a service-container DB.
- **CopilotKit ↔ Python not connecting** → check the AG-UI/SSE endpoint URL, CORS, and that the agent backend is actually running.

### 7.6 Stretch goals (after it works)
Rewrite the poller in **Go**; swap Redis Streams for **Kafka**; add **gRPC** between services; implement the Watchdog in **LangGraph** (checkpointing keyword); run on **k3s**; geofenced "your bus is 2 stops away" push alerts; **multi-city** (add NYC subway); **map-matching** noisy GPS (HMM/Viterbi); human-in-the-loop confirmation on higher-risk tools; voice input for the Copilot.

### 7.7 Learning resources (depth when you want it)
Official docs are your friend: **PostGIS** (docs + intro workshop), **PostgreSQL** (docs; "Use The Index, Luke" for indexing), **FastAPI** (incl. WebSockets), **Redis Streams** (intro), **H3**, **TimescaleDB**, **GTFS/GTFS-RT** (gtfs.org), **MapLibre GL JS**, **Docker** (get started), **Prometheus/Grafana**, **LightGBM** + scikit-learn (metrics), **Pydantic AI** (agents, tools, MCP, evals), **pgvector**, **CopilotKit** (AG-UI), **Langfuse**, and the **Model Context Protocol** spec. Primary loop: read the relevant Part 2 section → start the phase → have Claude Code teach each step → answer the Concept Check. Reach for a doc only when you want more than the phase needs.

---

## PART 8 — Final words & how to start

This document is a map, not a cage. Build in order, understand before you run, capture your numbers as you go, and ship something a stranger can open, talk to, and enjoy. The backend phases (0–9) give you a real, live system. The agentic phases (A–J) put a brain on it that interviewers will remember. Together they say the thing you want to say: *I can build the whole system, and I deeply understand agents.*

The point of the explain-before-execute rule is that, at the end, you won't just *have* a project — you'll be able to explain, defend, and extend every layer of it, from a GiST index to a corrective-RAG loop. That's the difference between vibe-coding and engineering, and it's exactly what the internships you're targeting are looking for.

**To start:** open Claude Code, paste this document as the first message, let it acknowledge the Part 0 rules, then paste the **Phase 0 kickoff prompt**. Build one phase at a time. Understand everything.

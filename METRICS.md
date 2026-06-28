# LiveTransit Copilot — Metrics

Real numbers captured during the build (for the README, résumé, and interviews).

## Body (LiveTransit)

### Spatial index speedup (Phase 2) — "vehicles within ~500 m of downtown Boston"
Query: `ST_DWithin(geom, ST_SetSRID(ST_MakePoint(-71.0589, 42.3601), 4326), 0.006)`
on `vehicle_positions` (~40,300 rows at time of measurement; 825–880 rows matched).

| | Query plan | Execution time (warm) |
|---|---|---|
| **Before index** | `Seq Scan` (every row) | ~89 ms (203 ms cold) |
| **After GiST index** | `Bitmap Index Scan` on `vehicle_positions_geom_gist` | ~1.4 ms (1.9 ms cold) |

**≈ 60× faster**, plan changed Seq Scan → Index Scan. Gap widens as the table grows.
Bonus: H3 neighborhood lookup (`WHERE h3_cell = ...`) uses an `Index Only Scan` at ~0.24 ms.

### Ingestion
- Live MBTA VehiclePositions ingested every ~10 s; ~500–760 vehicles per poll.
- Pipeline: poller → Redis Stream (`vehicles:stream`) → processor → PostGIS.
- Idempotent at-least-once processing: `INSERT ... ON CONFLICT (vehicle_id, recorded_at)
  DO NOTHING`. Verified **0 duplicate rows** under continuous re-publishing.

### ML arrival predictor (Phase 6) — LightGBM delay-propagation model
Framing: predict a vehicle's delay at an upcoming stop from its current (upstream) delay +
hour/day/route/stop_sequence. **Time-based split** (train on earlier ~80%, test on later ~20%)
to prevent leakage. Retrained 2026-06-28 on **full-day** data (~413k labels, 4 days incl. morning +
evening rush — vs the v1 evening-only ~30,800).

| Predictor | MAE (s) on held-out later period |
|---|---|
| Baseline: schedule (assume on-time) | 313.3 |
| Baseline: historical avg per route | 250.4 |
| Baseline: persistence (next = current) | 53.9 |
| **LightGBM model (v2, full-day)** | **45.4** |

**85.5% better than schedule**, **15.8% better than the strong persistence baseline**. CPU-trained
in seconds (no GPU). (v1 was 44.0 on evening-only data; v2's 45.4 is on the harder full-day
held-out period — a more honest, representative number.) Re-trains as more history accrues.

## Brain (Copilot)
_To be captured in the agentic phases (A–J): tool count, eval scores, agent latency,
tokens/cost per query, fallback behavior, RAG citation rate._

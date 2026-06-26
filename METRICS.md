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
to prevent leakage. ~30,800 clean labels (filtered |delay|≤30 min, approach <60 m).

| Predictor | MAE (s) on held-out later period |
|---|---|
| Baseline: schedule (assume on-time) | 249.3 |
| Baseline: historical avg per route | 203.7 |
| Baseline: persistence (next = current) | 48.7 |
| **LightGBM model** | **44.0** |

**82.3% better than schedule**, **9.6% better than the strong persistence baseline**. CPU-trained
in seconds (no GPU). Re-trains as more history accrues.

## Brain (Copilot)
_To be captured in the agentic phases (A–J): tool count, eval scores, agent latency,
tokens/cost per query, fallback behavior, RAG citation rate._

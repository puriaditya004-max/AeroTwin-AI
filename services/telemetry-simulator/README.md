# M1 — Telemetry Simulator

**Status:** Production-grade demonstrator  
**Produces:** `TelemetryFrame` on Redis Stream `telemetry.frame.v1`  
**Consumes:** nothing (YAML scenario configs only)

This service generates **synthetic** engine telemetry for AeroTwin-AI demos. It is
not a physics engine, not a digital twin of a certified powerplant, and not an
airworthiness source. Downstream modules should treat every frame as advisory
demonstrator data.

## Architecture

```
configs/m1.yaml ─┐
configs/scenarios/*.yaml ─┤
                          ▼
                 simulation/engine_model.py
                          │  TelemetryFrame
                          ▼
                 stream/publisher.py  ──► Redis Stream telemetry.frame.v1
                          ▲
           FastAPI API    │    worker process
           (start/stop)   │    (lease-backed publisher)
```

- `app/main.py` — FastAPI: health, scenario start/stop/list, metrics.
- `app/worker.py` — long-running publisher that follows API desired-state in Redis.
- `app/contracts.py` — local mirror of `packages/schemas` `TelemetryFrame`.
- `simulation/` — YAML-driven envelope, noise, replay seed.
- `stream/publisher.py` — Redis `XADD` with bounded backoff.

Only one process holds `m1:publisher-lease`, so API + worker can both be up
without double-publishing.

## Output contract (`TelemetryFrame`)

Canonical schema: `packages/schemas/json-schema/TelemetryFrame.schema.json`.

Required fields (exact names):

| Field | Notes |
| --- | --- |
| `engineId` | Engine instance id |
| `missionId` | Scenario run id |
| `correlationId` | Trace id for the whole mission (never dropped) |
| `timestamp` | UTC ISO 8601 sample time (replay uses a fixed epoch) |
| `sensors` | See below |
| `qualityFlag` | `OK` \| `DEGRADED` \| `DROPOUT` \| `DUPLICATE` \| `OUT_OF_ORDER` |
| `producerVersion` | From `configs/m1.yaml` |

Required sensors: `rpm`, `oilPressureKpa`, `oilTempC`, `coolantTempC`,
`vibrationMmS`, `fuelFlowLph`, `throttlePct`, `altitudeM`, `ambientTempC`,
`ambientPressureKpa`.

Optional v2 fields (`chtCylindersC`, `egtCylindersC`, electrical, injection)
are populated for richer demo streams. There is no `cylinderTempC` field;
cylinder/head temperature is `coolantTempC` plus optional `chtCylindersC`.

M1 publishes to **`telemetry.frame.v1`** (singular `frame`), matching M2 ingest.

JSON payload field on the stream: `payload` (plus `correlationId` / `qualityFlag`).

## Scenario catalog

| Id | Behaviour |
| --- | --- |
| `normal` | Stable readings inside a nominal envelope |
| `overheating` | `coolantTempC` / `oilTempC` rise after `fault.injectAfterSeconds` |
| `oil_pressure_degradation` | Golden demo: slow `oilPressureKpa` decline after offset |
| `vibration_misfire` | Intermittent `vibrationMmS` spikes after offset |
| `sensor_dropout` | Missing, duplicate, and out-of-order frames after offset |

Faults never start at t=0 unless `injectAfterSeconds` is set to `0` in YAML.

### How to add a new scenario

1. Add `configs/scenarios/<id>.yaml` with `id`, `nominal`, optional `fault.sensors`
   (`mode: linear` \| `spike` \| `hold`), and `quality` rates.
2. Reference it from `configs/m1.yaml` under `scenarios`.
3. Restart the service. No Python change is required for envelope/fault YAML.

## Replay seed behaviour

- Each scenario file has a default `seed`.
- `POST /scenarios/{name}/start` accepts `{ "seed": <int> }`.
- `correlationId` defaults to `corr-{scenario}-{seed}` so traces are stable.
- Sensor jitter and quality events use deterministic PRNGs.
- Timestamps are `publish.replayEpoch` + tick/rate, not wall clock, so the same
  seed yields identical frame payloads.

## Data quality simulation

Configured in `m1.yaml` defaults and overridden per scenario:

- `dropoutRate` — skip publish (true missing sample); generated frame still has `qualityFlag=DROPOUT`
- `dropoutFlagRate` — publish a `DROPOUT` marker frame
- `duplicateRate` — second copy with `qualityFlag=DUPLICATE`
- `outOfOrderRate` — earlier `timestamp` and `qualityFlag=OUT_OF_ORDER`
- `degradedRate` — `qualityFlag=DEGRADED`

The shared schema uses `DROPOUT`, not `MISSING`, for frame-level quality.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health/live` | Process liveness + run snapshot |
| `GET` | `/health/ready` | Publisher ping |
| `GET` | `/scenarios` | Catalog + status |
| `POST` | `/scenarios/{name}/start` | Start a run (`seed`, `missionId`, `correlationId` optional) |
| `POST` | `/scenarios/{name}/stop` | Stop that run |
| `GET` | `/metrics` | `framesSent`, `dropRate`, `currentScenario`, retries |

Port: **8001**.

## Run locally

```bash
cd services/telemetry-simulator
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Tests:

```bash
python -m pytest services/telemetry-simulator/tests
```

Start the golden demo:

```bash
curl -X POST http://localhost:8001/scenarios/oil_pressure_degradation/start \
  -H 'content-type: application/json' \
  -d '{"seed": 7}'
```

## Docker

From the repository root (Redis is pulled in via `depends_on`; no other AeroTwin
services are required):

```bash
docker compose up --build telemetry-simulator redis
```

Optional worker (takes over publishing if it wins the Redis lease):

```bash
docker compose up --build telemetry-simulator telemetry-simulator-worker redis
```

Healthcheck: `GET /health/live`.

Environment:

- `REDIS_URL` (default `redis://redis:6379/0`)
- `M1_OUTPUT_STREAM` (default `telemetry.frame.v1`)
- `M1_CONFIG_PATH`
- `M1_DEFAULT_SCENARIO` (worker-only auto-start)

## Safety limitation

All values are **synthetic**. They are shaped to stay inside the JSON Schema
ranges and to illustrate degradation patterns for a hackathon demonstrator.
They are **not** real engine physics, **not** certified limits, and **not**
an airworthiness or maintenance instruction.

## Known limitations

- Envelope interpolation is piecewise YAML, not a thermodynamic model.
- Redis must be reachable for stream publish and for `/health/ready` in Docker.
- Quality events are independent Bernoulli draws per tick, not bursty radio models.
- Optional v2 sensors are filled with demonstrator constants, not a wiring harness.
- If both API and worker run without Redis, they cannot coordinate a lease.

# M2 - Digital Twin and State Estimation

**Owner:** M2 | **Status:** Production-grade demonstrator implementation
**Consumes:** `telemetry.frame.v1` | **Produces:** `twin.state.v1`

M2 converts imperfect M1 telemetry into synchronized `TwinState` events for
M3, M4, M5, and M6. It owns synchronization, dedupe, rolling windows, state
estimation, quality assignment, latest-state API, Redis publishing, and
operational visibility. It does not predict faults, RUL, health rules, or
mission advisories.

## Build Gates

| Gate | Capability | Status |
| --- | --- | --- |
| 01 | Contract-safe service skeleton and config | Complete |
| 02 | Redis Streams consumer group `m2-twin-engine` | Complete |
| 03 | Schema validation, deterministic dedupe, late-frame guard | Complete |
| 04 | Per `engineId + missionId` rolling windows | Complete |
| 05 | Load, margins, and required derived features | Complete |
| 06 | GOOD / DEGRADED / STALE state quality policy | Complete |
| 07 | `twin.state.v1` publisher and latest-state API | Complete |
| 08 | In-process checkpoint plus Redis durable latest-state checkpoint | Complete |
| 09 | Docker Compose service + worker integration and pending-message recovery | Complete |
| 10 | Tests, sync-lag metrics, and explanation notes | Complete |

## Runtime

```powershell
cd C:\Users\puria\Downloads\AeroTwin-AI
docker compose up --build twin-engine twin-engine-worker redis
```

Local API:

- `GET http://localhost:8002/health/live`
- `GET http://localhost:8002/health/ready`
- `GET http://localhost:8002/state/latest`
- `GET http://localhost:8002/state/{engineId}`
- `GET http://localhost:8002/state/{engineId}/{missionId}`
- `GET http://localhost:8002/metrics`

Metrics include consumed/rejected/deduped/late frames, publish failures,
published state count, last sync lag, average sync lag, and p95 sync lag.

## Development

```powershell
cd services\twin-engine
python -m pip install -e .[dev]
pytest
```

## Contract Lock

M2 keeps the shared `TelemetryFrame` and `TwinState` fields unchanged:

- Preserves `engineId`, `missionId`, `correlationId`, and event timestamp.
- Reads `telemetry.frame.v1`.
- Publishes `twin.state.v1`.
- Emits `TwinState.stateQuality` as `GOOD`, `DEGRADED`, or `STALE`.
- Uses the required `margins` and `derivedFeatures` objects.
- Adds optional v2 telemetry for CHT/EGT cylinders, alternator, battery,
  injection timing, and per-sensor quality metadata.
- Uses `configs/engine_profile.sih-demo.yaml` for demonstrator-only operating
  limits and feature calculations.

Any future schema change requires a matching JSON Schema update and ADR in
`docs/decisions/`.

## Judge Explanation

M2 is the synchronized engine state layer. Bad or late telemetry does not become
a fake fresh state. Instead, the state quality degrades or becomes stale, while
the latest trustworthy rolling-window context is preserved for downstream
modules.

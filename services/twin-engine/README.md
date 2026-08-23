# M2 — Digital Twin & State Estimation

**Owner:** TBD | **Workload:** 16% | **Commitment:** Core MVP
**Branch:** `feature/digital-twin`

## Problem Owned
Maintain a continuously synchronized virtual engine state from imperfect telemetry.

## Stack
Python 3.12, FastAPI, Pydantic, NumPy, SciPy, Redis client, PostgreSQL/TimescaleDB, Pytest

## Implementation Checklist
- [ ] Consume `TelemetryFrame` events; align timestamps, units, mission identifiers
- [ ] Maintain latest state, rolling windows, derived load/temperature/pressure margins
- [ ] Implement missing-value policy, stale-state detection, state-quality scoring
- [ ] Expose `TwinState` via internal API; publish `state.updated` events
- [ ] Persist selected state snapshots (not every duplicate calculation)
- [ ] Measure synchronization lag; provide health endpoint

## Required Outputs
- twin-engine service
- `TwinState` contract
- State snapshot writer
- Sync metrics

## Acceptance Tests
- Timestamp alignment
- Stale state handling
- Restart recovery
- Target update lag met

## Contracts
- **Consumes:** `TelemetryFrame` from M1
- **Produces:** `TwinState`: `stateTime, load, margins, derivedFeatures, stateQuality` → **consumed by M3/M4/M5**

## Judge Explanation Responsibility
How telemetry becomes synchronized state, how missing data affects confidence, why a digital twin is more than a live chart.

## Handoff
Consumes M1 frames. Provides `TwinState` to M3, M4, M5. Exposes health status to M6.

# M1 — Telemetry Ingestion & Simulator

**Owner:** TBD | **Workload:** 15% | **Commitment:** Core MVP
**Branch:** `feature/telemetry-simulator`

## Problem Owned
Create safe, documented, repeatable engine telemetry streams for normal and degraded mission scenarios.

## Stack
Python 3.12, NumPy, Pandas, Pydantic, Redis Streams, Pytest, Docker Compose

## Implementation Checklist
- [ ] Define canonical `TelemetryFrame` schema, units, valid ranges, quality flags
- [ ] Generate RPM, temperatures, pressure, vibration, fuel flow, throttle, altitude, ambient conditions
- [ ] Implement 5 scenarios: normal, overheating, oil-pressure degradation, vibration/misfire, sensor-dropout
- [ ] Publish timestamped frames at configurable rate; support deterministic replay seeds
- [ ] Handle invalid values, missing samples, duplicates, out-of-order timestamps
- [ ] Docker health check, sample data, scenario documentation

## Required Outputs
- Simulator service
- `TelemetryFrame` schema
- 5 replay manifests
- Redis publisher

## Acceptance Tests
- Schema validation
- Repeatable seed output
- Dropout recovery
- Stream rate target met

## Contract Produced
`TelemetryFrame`: `engineId, missionId, timestamp, sensors, qualityFlag` → **consumed by M2**

## Judge Explanation Responsibility
Where does data come from, what does each sensor mean, how are faults injected, why is this not claimed as certified engine physics.

## Handoff
Hands validated `TelemetryFrame` events to Member 2. Shares Docker/Redis setup with Member 6.

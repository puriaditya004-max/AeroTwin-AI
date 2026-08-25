# M6 — Control API (part of Mission Reliability, HMI & Integration)

**Owner:** Aditya Puri | **Workload:** 20% (highest — expect real load ~30-35%) | **Commitment:** Core MVP
**Branch:** `feature/operator-hmi`

## Problem Owned
Combine every module into one secure operator product that provides live status, explanation, replay, and traceable advisory. This service is the backend half; see `apps/operator-hmi/` for the frontend half.

## Stack
Node.js LTS, Express, TypeScript, Prisma, Socket.IO, PostgreSQL, Docker Compose

## Implementation Checklist
- [x] Extract auth, RBAC, realtime, storage patterns from FocusForge — no unrelated product logic
- [x] Implement control API, mission/session entities, advisory rules, audit logs, Socket.IO events
- [x] Build `Continue / Reduce Load / Inspect` advisory states — **no autonomous control**
- [x] Add ingest idempotency for upstream retry safety
- [x] Recompute advisories from Health, Fault, and RUL arrivals
- [ ] Own Docker Compose, environment template, CI checks, one-command local demo
- [ ] Coordinate interface freezes, integration merges, pitch flow, backup recording

## Required Outputs
- Control API
- `MissionAdvisory` contract
- Integrated Docker demo

## Acceptance Tests
- RBAC and audit
- Realtime UI
- Mission replay
- Fresh-machine startup

## Contracts
- **Consumes:** all module contracts (`TelemetryFrame`, `TwinState`, `HealthSnapshot`, `FaultPrediction`, `RulEstimate`)
- **Produces:** `MissionAdvisory`: `risk, action, explanation, inspectionRequired` → **consumed by HMI**

## Judge Explanation Responsibility
Full architecture, why each technology was chosen, how all modules integrate, what the product deliberately does NOT claim.

## Handoff
Consumes all module contracts. Owns final product integration — does NOT rewrite unfinished modules for their owners.

## Production Codebase Notes

### Ingest Endpoints

- `POST /ingest/health` consumes `HealthSnapshot`, stores it, emits `health.updated`, and recomputes `MissionAdvisory`.
- `POST /ingest/fault` consumes `FaultPrediction`, stores it, emits `fault.predicted`, and recomputes the advisory when a health snapshot exists.
- `POST /ingest/rul` consumes `RulEstimate`, stores it, emits `rul.updated`, and now recomputes the advisory when a health snapshot exists.

All ingest endpoints auto-upsert `Engine` and `Mission` from the payload before persistence. This keeps upstream module retries from failing when the operator has not manually created the mission yet.

### Idempotency

Upstream workers should send `X-Idempotency-Key`. If absent, M6 derives a key from payload kind, mission id, correlation id, and event time.

- Same key + same payload hash: returns `202` with `duplicate: true`.
- Same key + different payload hash: returns `409 IDEMPOTENCY_CONFLICT`.
- Fresh key: event is persisted and broadcast normally.

The Prisma `IngestEvent` ledger backs this behavior so M2/M4/M5 retries do not create duplicate rows.

### Advisory Policy

Decision logic is split under `src/services/advisory/`:

- `policy.ts`: risk/action thresholds and decision factors.
- `explanation.ts`: operator-facing explanation text.
- `index.ts`: `MissionAdvisory` construction.

Policy considers health score/trend, health data quality, fault type/confidence/anomaly score, and experimental RUL cycles/lower bound. Explanations explicitly state the advisory is not autonomous control.

### Runtime Env

- `M6_ADVISORY_PRODUCER_VERSION`
- `M6_HEALTH_CRITICAL_THRESHOLD`
- `M6_HEALTH_HIGH_THRESHOLD`
- `M6_HEALTH_MEDIUM_THRESHOLD`
- `M6_FAULT_CRITICAL_CONFIDENCE`
- `M6_FAULT_HIGH_CONFIDENCE`
- `M6_RUL_CRITICAL_LOWER_BOUND`
- `M6_RUL_HIGH_CYCLES`
- `M6_RUL_MEDIUM_CYCLES`

### Socket Auth

Socket.IO accepts JWT through `socket.auth.token`. In production, unauthenticated socket connections are rejected. In non-production, unauthenticated sockets are allowed so demo mode and local development stay easy.

### Verification

- `npm run prisma:generate`
- `npm run build`

Remaining codebase gaps before final demo hardening: automated Control API tests, E2E integration proof, and production login UX beyond dev-login.

## ⚠️ Reality Check (own notes)
This is the highest-risk role, not just the highest-workload one. Every module funnels through here. Priorities:
1. Get contracts frozen and sample payloads exchanged in hour 0–3 — don't skip this.
2. Merge to `develop` continuously, not just at the end.
3. Record the backup demo well before the pitch — don't leave it to the last hour.
4. Keep a fallback single-scenario (oil-pressure degradation) path bulletproof even if others slip.

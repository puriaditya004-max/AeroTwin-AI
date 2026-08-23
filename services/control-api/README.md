# M6 — Control API (part of Mission Reliability, HMI & Integration)

**Owner:** Aditya Puri | **Workload:** 20% (highest — expect real load ~30-35%) | **Commitment:** Core MVP
**Branch:** `feature/operator-hmi`

## Problem Owned
Combine every module into one secure operator product that provides live status, explanation, replay, and traceable advisory. This service is the backend half; see `apps/operator-hmi/` for the frontend half.

## Stack
Node.js LTS, Express, TypeScript, Prisma, Socket.IO, PostgreSQL, Docker Compose

## Implementation Checklist
- [ ] Extract auth, RBAC, realtime, storage patterns from FocusForge — no unrelated product logic
- [ ] Implement control API, mission/session entities, advisory rules, audit logs, Socket.IO events
- [ ] Build `Continue / Reduce Load / Inspect` advisory states — **no autonomous control**
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

## ⚠️ Reality Check (own notes)
This is the highest-risk role, not just the highest-workload one. Every module funnels through here. Priorities:
1. Get contracts frozen and sample payloads exchanged in hour 0–3 — don't skip this.
2. Merge to `develop` continuously, not just at the end.
3. Record the backup demo well before the pitch — don't leave it to the last hour.
4. Keep a fallback single-scenario (oil-pressure degradation) path bulletproof even if others slip.

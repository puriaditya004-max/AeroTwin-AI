# AeroTwin AI
### Smart India Hackathon 2026 — PS ID: SIH26-26054

**Problem Statement:** AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs.

> Hackathon demonstrator only. No airworthiness, defence deployment or autonomous control claim.

---

## What This Product Does

A documented simulator drives a synchronized engine-health twin. The system detects degradation, predicts a likely fault, estimates an experimental RUL proxy, explains the result, and produces a traceable operator advisory.

**Required output chain:**
```
TelemetryFrame -> TwinState -> HealthSnapshot -> FaultPrediction -> RulEstimate -> MissionAdvisory
```

---

## Team & Module Ownership

| # | Module | Owner | Workload | Commitment |
|---|--------|-------|----------|------------|
| M1 | Telemetry ingestion + simulator | TBD | 15% | Core MVP |
| M2 | Digital twin state synchronization | TBD | 16% | Core MVP |
| M3 | Health monitoring + physics rules | TBD | 15% | Core MVP |
| M4 | Anomaly + fault prediction | TBD | 18% | Core MVP |
| M5 | Remaining Useful Life proxy + validation | TBD | 16% | Experimental |
| M6 | Mission reliability advisory + operator HMI | **Aditya Puri** | 20% | Core MVP |

Ownership rule: each member owns one module, its tests, documentation, and judge explanation. Member 6 owns final integration, but every module must expose its agreed contract before integration.

---

## Repository Layout

```
AeroTwin-AI/
├── apps/operator-hmi/          # M6 — React/TS/Vite/Tailwind dashboard
├── services/
│   ├── control-api/            # M6 — Node/Express/Prisma/Socket.IO
│   ├── twin-engine/            # M2 — FastAPI twin state service
│   ├── telemetry-simulator/    # M1 — Python simulator + Redis publisher
│   ├── health-monitor/         # M3 — physics rules engine
│   ├── fault-ai/               # M4 — anomaly + fault classifier
│   └── rul-validation/         # M5 — RUL regression + validation
├── packages/
│   ├── schemas/                # Shared contract schemas (Pydantic/Zod)
│   ├── auth/                   # RBAC/auth patterns (from FocusForge)
│   └── ui/                     # Shared UI components
├── models/
│   ├── anomaly/                # M4 model artifacts
│   ├── fault/                  # M4 model artifacts
│   └── rul/                    # M5 model artifacts
├── tests/
│   ├── unit/
│   ├── integration/
│   └── scenarios/               # 5 mandatory end-to-end scenarios
├── data/synthetic/              # Synthetic/approved public data only
├── docs/decisions/              # Architecture Decision Records (ADRs)
└── infra/                       # Docker Compose, CI configs
```

---

## Tech Stack

| Layer | Stack | Owner |
|---|---|---|
| Operator UI | React, TypeScript, Vite, Tailwind CSS, Recharts | M6 |
| Control API | Node.js LTS, Express, TypeScript, Prisma, Socket.IO | M6 |
| Twin API | Python 3.12, FastAPI, Pydantic, Uvicorn | M2 |
| Telemetry | Python, NumPy, Pandas, Redis Streams | M1 |
| Health logic | Python, NumPy, Pandas, SciPy, rules | M3 |
| Fault AI | scikit-learn, XGBoost, SHAP | M4 |
| RUL + MLOps | XGBoost, scikit-learn, MLflow | M5 |
| Data | PostgreSQL, TimescaleDB extension, Redis | M1/M2/M6 |
| Artifacts | MinIO locally; S3-compatible later | M5/M6 |
| Quality | Pytest, Vitest, Supertest, Playwright, k6 | All |
| Delivery | Docker Compose, GitHub Actions, structured logs | M1/M6 |

**Complexity rule:** No Kubernetes, Kafka, blockchain, or 3D game engine in the 36-hour MVP.

---

## Shared Contracts (Integration Boundary)

| Contract | Required Fields | Producer → Consumer |
|---|---|---|
| TelemetryFrame | engineId, missionId, timestamp, sensors, qualityFlag | M1 → M2 |
| TwinState | stateTime, load, margins, derivedFeatures, stateQuality | M2 → M3/M4/M5 |
| HealthSnapshot | healthScore, trend, violatedRules, reasonCodes | M3 → M5/M6 |
| FaultPrediction | faultType, confidence, anomalyScore, contributors, version | M4 → M5/M6 |
| RulEstimate | cycles, lowerBound, upperBound, trend, version | M5 → M6 |
| MissionAdvisory | risk, action, explanation, inspectionRequired | M6 → HMI |

**Rules:** Every contract has JSON Schema/Pydantic/Zod validation + version number. Timestamps in UTC ISO 8601. Sample payloads committed before implementation begins. No member changes a shared contract without a short ADR and review.

**Integration gate:** A module is complete only when it passes its contract tests AND the next module can consume its output without manual editing.

---

## Five Mandatory Scenarios

1. Normal operation — stable health, no false critical advisory
2. Gradual overheating — falling health, explainable temperature contribution
3. Oil-pressure degradation — early warning, fault prediction, inspection advisory
4. Abnormal vibration/misfire proxy — anomaly detection, confidence display
5. Sensor dropout — quality degradation without unsupported failure claim

**Priority tip:** If time runs short, get Scenario 3 (oil-pressure degradation) rock-solid end-to-end first — it's the golden demo journey. Treat the rest as stretch goals with a clear fallback.

---

## 36-Hour Execution Plan

| Window | Parallel Work | Integration Checkpoint |
|---|---|---|
| 0–3h | Freeze contracts, scenarios, branch rules, demo story | Skeleton services exchange one sample event |
| 3–8h | M1 simulator; M2 state; M3 rules; M4/M5 baselines; M6 shell | Normal scenario reaches dashboard |
| 8–16h | Complete module core paths + unit tests | Health + one fault end-to-end |
| 16–24h | Five scenarios, explanations, RUL proxy, replay | All contracts and metrics visible |
| 24–30h | Security, restart recovery, deployment, failure cases | Fresh-machine run passes |
| 30–34h | Fix only critical defects; finalize evidence and slides | Feature freeze |
| 34–36h | Pitch rehearsal, backup demo, role explanations | Final product handoff |

---

## Branch Model

| Branch | Owner |
|---|---|
| feature/telemetry-simulator | M1 |
| feature/digital-twin | M2 |
| feature/health-monitoring | M3 |
| feature/fault-prediction | M4 |
| feature/rul-validation | M5 |
| feature/operator-hmi | M6 |

No direct push to `main`. PRs require tests, module README, sample output. Review pairs: M1-M2, M3-M4, M5-M6. Critical contracts require M6 integration review. Merge to `develop` several times during the event — don't postpone all integration to the final hours.

---

## Definition of Done

- [ ] One command starts the complete local system + seeded demo
- [ ] Normal + four degraded scenarios reach the same operator HMI
- [ ] Every output includes timestamp, mission/engine id, component/model version
- [ ] Measured metrics clearly separated from proposed field targets
- [ ] No autonomous control, airworthiness, or real defence-data claim made
- [ ] All six members can explain their module and its integration boundary

## Data Discipline

Synthetic or approved public data only. Restricted, operational, or proprietary defence telemetry must not be uploaded to repositories or third-party AI services.

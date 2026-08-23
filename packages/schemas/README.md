# Shared Schemas

This package holds the versioned JSON Schema / Pydantic / Zod definitions for every contract crossing module boundaries.

## Rule
No member changes a shared contract without a short Architecture Decision Record (see `/docs/decisions/`) and review. Sample payloads must be committed here **before** module implementation begins.

## Status: LOCKED (v1) — 22 Aug 2026

All 6 contracts are defined in three parallel forms, kept in sync manually. Any change needs an ADR in `/docs/decisions/` first.

```
packages/schemas/
├── json-schema/          # Canonical, language-agnostic source of truth
│   ├── TelemetryFrame.schema.json
│   ├── TwinState.schema.json
│   ├── HealthSnapshot.schema.json
│   ├── FaultPrediction.schema.json
│   ├── RulEstimate.schema.json
│   └── MissionAdvisory.schema.json
├── python/
│   └── contracts.py       # Pydantic models — import into M1-M5 services
├── typescript/
│   └── contracts.ts       # Zod schemas — import into Control API (M6) + HMI
└── samples/
    └── *.sample.json      # One valid fixture per contract
```

## How each module uses this

- **M1 (Telemetry, Python):** `from contracts import TelemetryFrame, Sensors, QualityFlag`
- **M2 (Twin, Python/FastAPI):** `from contracts import TwinState, TelemetryFrame` (consume + produce)
- **M3 (Health, Python):** `from contracts import HealthSnapshot, TwinState`
- **M4 (Fault AI, Python):** `from contracts import FaultPrediction, TwinState`
- **M5 (RUL, Python):** `from contracts import RulEstimate, HealthSnapshot, FaultPrediction`
- **M6 (Control API, TypeScript):** `import { MissionAdvisorySchema, HealthSnapshotSchema, ... } from "./contracts"`
- **HMI (TypeScript/React):** same `contracts.ts`, for typing incoming Socket.IO payloads

## Verified (22 Aug 2026)
All 6 sample payloads pass validation against: JSON Schema (`jsonschema`), Pydantic (`contracts.py`), and Zod (`contracts.ts`, `tsc --strict` clean). Run `npm run validate-samples` inside `typescript/` to re-check after any edit.

## Common fields on every contract
`engineId`, `missionId`, `correlationId` (trace id shared across one mission's whole event chain), `producerVersion`. Timestamps are UTC ISO 8601. Consumers must ignore unknown additive fields but reject missing required fields.

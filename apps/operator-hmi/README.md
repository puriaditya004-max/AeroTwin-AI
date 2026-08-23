# M6 — Operator HMI (frontend half)

**Owner:** Aditya Puri | See `services/control-api/README.md` for full M6 scope.

## Stack
React, TypeScript, Vite, Tailwind CSS, Recharts

## Implementation Checklist
- [ ] Live dashboard: telemetry, health, fault, RUL, explanation, mission replay
- [ ] Real-time updates via Socket.IO events: `health.updated`, `fault.predicted`, `advisory.updated`
- [ ] Advisory display: `Continue / Reduce Load / Inspect` states with contributing sensors
- [ ] Mission replay view from fixed scenario manifests
- [ ] Error handling for degraded/missing data states (sensor dropout scenario)

## Contract Consumed
`MissionAdvisory`: `risk, action, explanation, inspectionRequired` (from Control API)

## Judge Explanation Responsibility
How the operator reads risk state, how the explanation ties back to specific sensors, why this is advisory-only.

---

## Implementation Status (skeleton, 22 Aug 2026)

### Setup

```bash
cd apps/operator-hmi
npm install
cp .env.example .env
npm run dev          # http://localhost:5173
```

Runs in **DEMO mode by default** (`VITE_HMI_MODE=DEMO` in `.env.example`) — the dashboard renders fully with embedded mock data, no Control API connection needed. Set `VITE_HMI_MODE=LIVE` once M3/M4/M5 are producing real data end-to-end and you want to connect to the real Socket.IO stream.

### File layout

```
src/
├── App.tsx                    # Wires everything together, DEMO/LIVE toggle
├── main.tsx                   # React entrypoint
├── vite-env.d.ts              # Vite env typing
├── types/contracts.ts         # Copied from packages/schemas/typescript (see note in file header)
├── hooks/useMissionSocket.ts  # Socket.IO client hook (health.updated, fault.predicted, advisory.updated)
├── lib/mockData.ts            # Embedded demo/offline data, mirrors packages/schemas/samples/*.sample.json
├── components/
│   ├── TopBar.tsx             # Mission identity + connection/demo status
│   ├── RiskBanner.tsx         # Primary advisory: risk + action + explanation
│   ├── HealthGauge.tsx        # Signature element — custom SVG radial engine-health dial
│   ├── FaultPanel.tsx         # Fault type, confidence bar, top contributors
│   ├── RulPanel.tsx           # RUL cycles estimate + confidence range (marked experimental)
│   ├── TelemetryGrid.tsx      # 4 sparkline cards (RPM, oil pressure, oil temp, vibration) via Recharts
│   └── AuditLog.tsx           # Advisory history trail
└── styles/index.css           # Design tokens (Tailwind @layer base) + global styles
```

### Design system
Dark cockpit/avionics-instrument aesthetic — deliberately not a generic SaaS dashboard, since this is literally an operator instrument panel.
- **Palette:** graphite-blue background (`#0A0E13`) with an aviation caution-light system: green `#3DDC84` (CONTINUE/safe), amber `#FFB020` (REDUCE_LOAD/caution), red `#FF4D4D` (INSPECT/CRITICAL) — these map directly to the `risk`/`action` enum values, not arbitrary decoration.
- **Type:** Space Grotesk (headers) + IBM Plex Sans (body) + IBM Plex Mono (all telemetry/data readouts).
- **Signature element:** `HealthGauge.tsx` — a hand-built SVG arc dial with color-zoned banding and an animated needle, modeled on a real engine instrument rather than a generic circular progress ring.

### ⚠️ Verification status — read before trusting this blindly
- **`npx tsc --noEmit`**: actually run, zero errors, confirmed in the sandbox this was built in.
- **`npm run build`**: actually run, production Vite build succeeds (867 modules transformed, ~5.9s). Bundle is ~573KB unminified-equivalent / ~167KB gzipped — fine for a hackathon demo, but consider code-splitting if it grows.
- **Visual check**: actually rendered via a headless browser and screenshotted in the build sandbox — the dashboard displays correctly with demo data (health gauge, risk banner, fault/RUL panels, telemetry sparklines, audit trail all confirmed visible and readable).
- **Not yet tested:** real Socket.IO connection against a running Control API with a live database (needs `services/control-api` fully running with Postgres — do this once both are on your machine together).

### Known gaps to fill next
- No mission replay/scrubber UI yet (doc requires this — `MissionReplay` component not built).
- `RulPanel` isn't wired to a live socket event yet — RUL doesn't have a dedicated Socket.IO event in `services/control-api/src/sockets/index.ts`; either add one or fetch it via a REST endpoint on mount.
- No initial REST fetch on mount for `/missions/:id/advisories/latest` — right now LIVE mode only shows data after the *first* Socket.IO event arrives, so a page refresh mid-mission shows nothing until the next update. Fix before the fresh-machine demo.
- No error/empty states for sensor dropout scenario yet (doc's 5th mandatory scenario) — `TelemetryGrid` doesn't visually distinguish `qualityFlag: DROPOUT` from normal data yet.

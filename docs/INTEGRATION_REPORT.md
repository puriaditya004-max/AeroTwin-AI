# Local integration verification report

Historical report for the first integration commit. Follow-up model and Docker
verification is recorded in [PRE_E2E_REPORT.md](PRE_E2E_REPORT.md); it supersedes
the Docker-availability and oil-pressure-recall status below.

2026-09-07. Branch `integration/e2e`, base `c115e38`. Working-tree changes are
uncommitted for review. No GitHub push, merge or remote write was performed.

**Status: local implementation and contract checks ready for review; full final
integration is NOT signed off.** Docker is absent, and the learned M4 model does
not yet reliably identify the oil-pressure class on the actual simulator inputs.

## Implemented

- Ported M1 simulator/scenarios and M5 branch changes; consolidated 14 Compose
  services/jobs, preserving M2/M4/M6 and adding the M3/M5 handoff adapter.
- Fixed M1 live clock, per-frame correlation, dropout flag and schema serialization.
  Aligned nominal synthetic oil pressure with M2's profile.
- M3 shared contracts, correctly scaled margins, quality-aware health output and
  raw oil/coolant thresholds; explicit rule version and documented review points.
- M5 canonical `/estimate`, matching upstream IDs/time, repeatable output, opt-in
  experimental proxy and honest readiness failure when no model/fallback exists.
- M2 durable API visibility and transactional output/checkpoint/window/dedupe/ACK.
- M3/M5 durable outbox and partial-handoff retry. M4 cached retry payloads and
  durable rolling context. Pinned M4 artifact dependency versions; eliminated
  unconditional training on container startup.
- Conservative M4 physical corroboration suppresses demonstrated false overheating
  on normal inputs. It does not invent an alternative fault class or probability.
- Explicit local-demo viewer login, real LIVE telemetry and quality indication,
  durable advisory replay, reconnect/refresh synchronization and expired-token recovery.
- Local startup script, loopback bindings, Redis persistence and updated docs.

## Checks actually run

| Check | Result |
| --- | --- |
| M1 `python -m pytest -q` | 21 passed |
| M2 `python -m pytest -q` | 18 passed |
| M3 `python -m pytest -q` | 7 passed |
| M4 `python -m pytest -q` | 26 passed |
| M5 `python -m pytest -q` | 60 passed |
| M3/M5 adapter `python -m pytest -q` | 1 passed |
| Control API `npm ci`, `npm run prisma:generate`, `npm run build`, `npm test` | Build passed; 48 tests passed |
| HMI `npm ci`, `npm run typecheck`, `npm run build` | Passed; final build defaults to LIVE |
| `python scripts/contract-smoke.py` | 2,419 JSON Schema checks passed using real module output |
| Compose YAML parse/service inventory | Parsed; 14 services/jobs |
| `git diff --check` | Passed |
| `docker compose config/build/up`, migrations and actual container health | NOT RUN: Docker executable absent |
| Full HTTP/Redis/PostgreSQL/browser E2E and live screenshots | NOT RUN; no claim of final E2E success |

Total: **181 passing tests**, plus **2,419 schema checks**. Tests with fake Redis or
mocked Prisma verify boundary/recovery behavior; they do not verify a real database
or Docker deployment. Contract smoke uses isolated processes, real models and
FastAPI TestClient; simulated clock aligns historical replay for pre-E2E validation.

The first HMI build hit a Windows sandbox path-resolution error; the same build
passed with approved local filesystem access. Existing FastAPI deprecation warnings
and the HMI bundle-size warning remain. npm install reported existing dependency
audit findings (API: 8; HMI: 2); no broad/forced dependency upgrade was performed.

## Scenario evidence (pre-E2E module checks only)

| Scenario | States checked | Health behavior | M4 sampled classes |
| --- | ---: | --- | --- |
| Normal | 120 | First warm-up score 90; subsequent scores 100 | NONE |
| Oil-pressure degradation | 120 | Minimum 63; pressure rule triggered | NONE, OVERHEATING; expected oil-pressure class absent |
| Overheating | 120 | Minimum 88; temperature warning triggered | NONE, OVERHEATING |
| Vibration/misfire | 120 | Minimum 85; vibration rule triggered | NONE, VIBRATION_MISFIRE |
| Sensor dropout | 107 | Quality warning; no physical rule inferred from bad quality | NONE |

All RUL outputs in this run were explicitly experimental RULE_BASED_PROXY.
M4 samples every tenth state with a rolling window; these are not full live
scenario acceptance results or measured real-engine performance.

## Remaining work before final sign-off

1. Correct/calibrate M4 oil-pressure recall against actual M1->M2 feature
   distributions, then rerun semantic checks. Artifacts were preserved. The
   corroboration fix removes unsupported labels but does not solve model recall.
2. Run Docker image builds, clean migrations, service health checks, real ingest
   202/duplicate/409 checks and refresh/restart recovery against Redis/PostgreSQL.
3. Run all five final E2E scenarios through the LIVE HMI and capture evidence.
4. Review M3 threshold adaptation, M4 corroboration, and M5 proxy/units with owners.

Operational limits: supplied topology is single-worker; Redis outbox/dedupe retention
is unbounded for the bounded local demo; sparkline history starts from latest state
after refresh, while advisory history persists. Deployment auth is not implemented
by the passwordless local-demo endpoint. Detailed decisions and startup commands:
[LOCAL_INTEGRATION.md](LOCAL_INTEGRATION.md),
[005-local-integration.md](decisions/005-local-integration.md).

## Suggested local commit sequence after review

1. M1 service port, scenarios, clock and quality fixes.
2. M2 shared checkpoint/transaction recovery and M3 canonical boundary.
3. M5 canonical estimate and M3/M5 outbox adapter.
4. M4 runtime artifacts, recovery and regression corroboration.
5. M6 local auth and actual LIVE state/replay.
6. Compose, startup, regression tests and verification documentation.

## Exact changed/added files

- `.dockerignore`
- `.env.example`
- `.gitignore`
- `README.md`
- `apps/operator-hmi/Dockerfile`
- `apps/operator-hmi/src/App.tsx`
- `apps/operator-hmi/src/components/TelemetryGrid.tsx`
- `apps/operator-hmi/src/hooks/useMissionSocket.ts`
- `docker-compose.yml`
- `docs/INTEGRATION_REPORT.md`
- `docs/LOCAL_INTEGRATION.md`
- `docs/decisions/005-local-integration.md`
- `scripts/contract-smoke.py`
- `scripts/start-local.ps1`
- `services/control-api/src/routes/auth.ts`
- `services/control-api/src/routes/mission.ts`
- `services/control-api/tests/integration/ingest.test.ts`
- `services/control-api/tests/integration/local-demo.test.ts`
- `services/control-api/tests/integration/mission.test.ts`
- `services/fault-ai/Dockerfile`
- `services/fault-ai/app/contracts.py`
- `services/fault-ai/app/main.py`
- `services/fault-ai/app/worker.py`
- `services/fault-ai/models/fusion.py`
- `services/fault-ai/pyproject.toml`
- `services/fault-ai/tests/unit/test_full_pipeline.py`
- `services/fault-ai/tests/unit/test_production_m4.py`
- `services/fault-ai/tests/unit/test_redis_m6_handoff.py`
- `services/health-monitor/Dockerfile`
- `services/health-monitor/main.py`
- `services/health-monitor/requirements.txt`
- `services/health-monitor/test_health_rules.py`
- `services/integration-worker/Dockerfile`
- `services/integration-worker/test_worker.py`
- `services/integration-worker/worker.py`
- `services/rul-validation/Dockerfile`
- `services/rul-validation/app/config.py`
- `services/rul-validation/app/main.py`
- `services/rul-validation/app/predictor.py`
- `services/rul-validation/app/rul_contract.py`
- `services/rul-validation/app/schemas.py`
- `services/rul-validation/requirements-runtime.txt`
- `services/rul-validation/tests/conftest.py`
- `services/rul-validation/tests/test_canonical_runtime.py`
- `services/rul-validation/tests/test_contracts.py`
- `services/rul-validation/tests/test_model_fallback.py`
- `services/telemetry-simulator/.dockerignore`
- `services/telemetry-simulator/Dockerfile`
- `services/telemetry-simulator/README.md`
- `services/telemetry-simulator/app/__init__.py`
- `services/telemetry-simulator/app/contracts.py`
- `services/telemetry-simulator/app/logging.py`
- `services/telemetry-simulator/app/main.py`
- `services/telemetry-simulator/app/runtime.py`
- `services/telemetry-simulator/app/settings.py`
- `services/telemetry-simulator/app/worker.py`
- `services/telemetry-simulator/configs/m1.yaml`
- `services/telemetry-simulator/configs/scenarios/normal.yaml`
- `services/telemetry-simulator/configs/scenarios/oil_pressure_degradation.yaml`
- `services/telemetry-simulator/configs/scenarios/overheating.yaml`
- `services/telemetry-simulator/configs/scenarios/sensor_dropout.yaml`
- `services/telemetry-simulator/configs/scenarios/vibration_misfire.yaml`
- `services/telemetry-simulator/pyproject.toml`
- `services/telemetry-simulator/simulation/__init__.py`
- `services/telemetry-simulator/simulation/engine_model.py`
- `services/telemetry-simulator/simulation/noise.py`
- `services/telemetry-simulator/simulation/scenarios.py`
- `services/telemetry-simulator/simulation/seed.py`
- `services/telemetry-simulator/stream/__init__.py`
- `services/telemetry-simulator/stream/publisher.py`
- `services/telemetry-simulator/tests/conftest.py`
- `services/telemetry-simulator/tests/unit/test_api.py`
- `services/telemetry-simulator/tests/unit/test_contracts.py`
- `services/telemetry-simulator/tests/unit/test_live_clock.py`
- `services/telemetry-simulator/tests/unit/test_noise.py`
- `services/telemetry-simulator/tests/unit/test_publisher.py`
- `services/telemetry-simulator/tests/unit/test_replay_seed.py`
- `services/telemetry-simulator/tests/unit/test_scenarios.py`
- `services/twin-engine/app/main.py`
- `services/twin-engine/app/worker.py`
- `services/twin-engine/state/estimator.py`
- `services/twin-engine/storage/checkpoint.py`
- `services/twin-engine/stream/publisher.py`
- `services/twin-engine/tests/unit/test_api.py`
- `services/twin-engine/tests/unit/test_restart_integration.py`

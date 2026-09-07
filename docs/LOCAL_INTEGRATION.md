# Run the local integration

Windows prerequisites: PowerShell 7, Docker Desktop running Linux containers,
Docker Compose v2.20 or later. Docker was not available on the integration machine;
container image builds, migrations, service health and final E2E require validation.

From the repository root:

```powershell
./scripts/start-local.ps1
```

The script generates an ignored `.env` with random local secrets if absent,
explicitly enables laptop demo authentication and the experimental RUL proxy,
validates Compose and starts the stack. Existing `.env` files are preserved.
Open http://localhost:5173/?missionId=MSN-LIVE-001. The normal synthetic run starts
automatically, lasts 120 seconds and then stops. Telemetry becomes STALE after
five seconds without new data. Initial M2 warm-up requires two samples.

For manual configuration, copy `.env.example`, replace placeholders, and set the
local flags as explained there before `docker compose up --build`.

## Runtime map

| Service | Input | Output / host endpoint |
| --- | --- | --- |
| telemetry-simulator | Scenario start/stop commands | http://localhost:8001/scenarios |
| telemetry-simulator-worker | Redis desired scenario | telemetry.frame.v1 |
| twin-engine-worker | telemetry.frame.v1 | twin.state.v1 + durable checkpoint |
| twin-engine | Redis checkpoint | http://localhost:8002/state/latest |
| health-monitor | POST /evaluate TwinState | HealthSnapshot, port 8003 |
| fault-ai + fault-ai-worker | twin.state.v1 | FaultPrediction -> M6 /ingest/fault, port 8004 |
| rul-validation | POST /estimate matching state + health | RulEstimate, port 8005 |
| health-monitor-worker | twin.state.v1 | Calls M3 + M5; posts /ingest/health and /ingest/rul |
| control-api | HTTP ingest + PostgreSQL | REST, Socket.IO, port 4000 |
| operator-hmi | Authenticated M6 REST/Socket.IO | LIVE dashboard, port 5173 |
| timescaledb, redis, migrate | Infrastructure | PostgreSQL persistence, Redis AOF, idempotent seed job |

All published ports bind to loopback. JSON is transported in Redis field `payload`.
Fault stream consumer group is m4-fault-ai; health/RUL adapter group is m3-m5-handoff.
M2 group is m2-twin-engine. Use a single worker for each supplied service.

## Start a different scenario

Stop the currently selected run before switching. Keep one mission ID per run and
use the returned missionId in the HMI URL. Example golden oil-pressure journey:

```powershell
Invoke-RestMethod -Method Post http://localhost:8001/scenarios/normal/stop
$run = Invoke-RestMethod -Method Post http://localhost:8001/scenarios/oil_pressure_degradation/start -ContentType application/json -Body '{"seed":42,"missionId":"MSN-OIL-DEMO-001"}'
$run
# Open http://localhost:5173/?missionId=MSN-OIL-DEMO-001
```

Other scenario IDs: overheating, vibration_misfire, sensor_dropout. Repeat with a
new mission ID and stop the previous scenario explicitly. HMI refresh loads the
saved health/fault/RUL/advisory state and latest telemetry; sparkline history then
accumulates the most recent 120 polled measurements. Advisory replay is persistent.

## Validation order

Run each Python service suite separately, because several services use an `app`
package. Install its declared dependencies in an isolated Python 3.12 environment.
Additional test dependencies: pytest, pytest-asyncio, fakeredis, jsonschema, httpx.

```powershell
# In services/control-api
npm ci
npm run prisma:generate
npm run build
npm test
# In apps/operator-hmi
npm ci
npm run typecheck
npm run build
# In each Python service directory
python -m pytest -q
# At repository root: real in-process module contract checks, NOT full E2E
python scripts/contract-smoke.py
docker compose config --quiet
docker compose build
docker compose up -d --wait --wait-timeout 300
docker compose ps
```

Only after these checks pass, validate full E2E in order: normal, oil-pressure
degradation, overheating, vibration/misfire, sensor dropout. Verify the same HMI
receives all outputs; normal has no critical advisory; quality faults do not claim
an engine failure; IDs remain traceable; refresh recovers state. Restart
`twin-engine-worker` mid-run and inspect pending/output counts and unchanged
idempotency. Capture logs and HMI screenshots for each scenario. These final
Docker/browser tests have not been claimed passed by the local implementation.

## Troubleshooting and shutdown

```powershell
docker compose ps
docker compose logs --tail 100 health-monitor-worker fault-ai-worker twin-engine-worker
docker compose exec redis redis-cli XLEN integration.dlq.v1
docker compose exec redis redis-cli XLEN fault.prediction.dlq.v1
docker compose down
```

`down` preserves named database/Redis volumes. Outboxes and dedupe keys intentionally
persist. Do not clear them while retaining the old ingest database and replaying
old events. No automated destructive reset is included.

Review [boundary decisions](decisions/005-local-integration.md) for model/rule owner
review points and demo-only limits. No remote push or merge was performed.

# Local M1-M6 integration

Date: 2026-09-07. Base: main c115e38. Local branch: integration/e2e.

The M1 and M5 service trees were ported from their feature branches. Compose was
consolidated from main so M2/M4/M6 services were retained. No remote changes were made.

## Boundary decisions

- M3 accepts the shared TwinState and produces the shared HealthSnapshot. The
  existing temperature/pressure/vibration/quality weights (30/30/25/15) remain.
  Threshold comparisons use M2's kPa and mm/s margins, not guessed bar/RMS units.
  CHT warning/critical limits are 205/230 C; vibration limits are 8/12 mm/s.
  Raw oil/coolant measurements use their separate warning/critical limits from
  the committed M2 demo profile. Bad-quality data produces a quality warning,
  suppressing unsupported physical-failure claims. These boundary rule corrections
  are versioned sih-margin-rules@1.1.0 and should be reviewed by the M3 owner.
- M2 forwards optional `sensors` and `qualityFlag` metadata in TwinState. Existing
  contracts permit additional properties. Required fields and ML features are
  unchanged. Metadata is measured M1 input; the HMI and M5 do not reconstruct sensors.
- M1 synthetic oil-pressure baselines are 430 kPa, matching the M2 nominal test
  envelope. The former 215 kPa baseline was below the load-adjusted minimum and
  caused nominal runs to report low pressure. Fault trajectories still end at their
  original degraded values. Live events use current UTC time and per-frame
  correlation IDs; replay retains its deterministic epoch and seed.
- M5 first loads a local model/scaler. MLflow is opt-in. Without artifacts, only an
  explicit M5_ALLOW_EXPERIMENTAL_FALLBACK=true enables the health-index proxy:
  `cycles = 300 * (healthScore / 100)^2`, bounded by the existing 15% interval.
  Outputs identify RULE_BASED_PROXY and experimental:health-proxy@1.0.0. This is
  a deterministic demonstration estimate, not a trained/calibrated lifetime model.
  Learned model/scaler calibration in canonical sensor units remains owner review.
- Local demo RUL advisory thresholds are 50/100/200 cycles, matching the proxy's
  0-300 scale. Deployment defaults remain unchanged. The startup script writes
  these explicit local values; it never commits generated secrets.
- M4 committed artifacts declare scikit-learn 1.9.0 and XGBoost 3.4.1. Runtime
  dependencies are pinned to those versions; artifacts and classifier logic are
  preserved. The worker caches predictions before ingest, preserving retry payloads.

## Recovery and authentication

M2 uses a Redis transaction for stream output, latest checkpoint, rolling window,
dedupe marker and input acknowledgement. Its API reads Redis, including after restart.
Run one M2 worker (the supplied Compose topology); horizontal replicas are not supported
by this transaction's read-before-write dedupe design. Redis AOF and a named volume
preserve checkpoints. Outboxes/dedupe keys remain for the local demo's lifetime and
need a retention policy for extended operation.

The health-monitor-worker is also the minimal M5 handoff adapter. It calls M3, then
M5 with matching state/health, saves both outputs, posts health and RUL to M6, and
acknowledges only after both return 202. Fault inference remains in its separate M4
service/worker. Pending events recover after retry idle time; DLQ streams preserve
malformed or repeatedly failing messages for inspection.

`/auth/demo-login` is available only with APP_MODE=local-demo AND
ENABLE_DEMO_AUTH=true. It issues VIEWER tokens regardless of submitted role.
The old development-login endpoint remains disabled in production. Published
Compose ports bind to 127.0.0.1. Real deployment authentication remains a separate
requirement; the passwordless demo path is not a production login system.

LIVE HMI uses authenticated REST snapshots, Socket.IO notifications, and periodic
resynchronization. It polls actual M2 measurements through M6 and labels stale or
unavailable telemetry. DEMO retains offline fixtures; LIVE has no mock fallback.


## Proven M4 semantic regression and conservative corroboration

Real committed model inference on M1->M2 outputs (not mocked data) classified some
normal frames as OVERHEATING. The training data's oil-temperature rate distribution
differs from the simulator's jitter-derived rates. The added M4 fusion guard only
suppresses a physical class when measured inputs provide no independent support:
CHT margin <25 C, oil >115 C or coolant >110 C for heat; negative pressure margin
for oil pressure; vibration margin <4 mm/s for vibration. It never invents another
class or a calibrated probability. Suppressed class confidence is zero, while the
measured anomaly score remains visible. Producer version identifies the gate.

This is not model recalibration. Oil-pressure classification recall and normal
anomaly rates remain module-owner review items. No existing model was retrained
or replaced. The Dockerfile now copies the promoted artifacts and starts the API
without its former unconditional training-on-boot command.

### Follow-up: synthetic calibration v2

The subsequent pre-E2E follow-up adds artifacts/v2 and explicitly selects it in
Compose. It trains on real M1/M2 synthetic outputs with disjoint mission seeds,
adding measured oil/coolant temperatures to distinguish heat onset. Shared scenario
templates and threshold-derived labels mean these scores are module regressions,
not independent real-world validation. v1 is retained. See PRE_E2E_REPORT.md and
the v2 model card for current evidence and scope.

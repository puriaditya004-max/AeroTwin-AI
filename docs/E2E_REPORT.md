# Local synthetic E2E verification — 8 September 2026

PASS for five synthetic scenario journeys through M1 → Redis → M2 → M3/M4/M5 → PostgreSQL/control API → operator HMI.

| Scenario | Result |
| --- | --- |
| Normal | NONE; stable health 100 after warm-up; no critical advisory |
| Oil pressure degradation | OIL_PRESSURE_DEGRADATION; minimum health 63; CRITICAL / Inspect |
| Overheating | OVERHEATING; minimum health 88; CRITICAL / Inspect |
| Vibration/misfire | Intermittent VIBRATION_MISFIRE; minimum health 85; spike verified in replay |
| Sensor dropout | Quality issue; minimum health 90; no physical-fault claims |

Each scenario used seed 42 and a 120-second sequence. Initial normal warm-up briefly produced a conservative MEDIUM quality advisory.

592 unique twin states produced 592 health, 592 fault and 592 RUL database records (1,776 outputs). Database ledger matched; duplicate persisted outputs were zero. Dropout included 122 frames with 112 unique IDs; all 112 reached M2 exactly once. Sampled downstream records traced to source frame IDs.

Restarting the twin worker during normal processing lost no frames. Stopping/restarting the control API during dropout showed a disconnected dashboard, automatic reconnect, and eventual delivery of all records. Final pending queues, lag and both dead-letter streams were zero. All 14 long-running containers were healthy; migration exited zero.

Dashboard refresh restored all five missions. Replay playback and keyboard scrubbing worked. Stale warnings appeared when streams stopped. A dense timeline-marker click timed out in automation; pointer usability remains a minor follow-up.

Validation: 135 Python tests, 48 control API tests, and 2,419 cross-module schema checks passed. API build, HMI typecheck/build and HTTP/PostgreSQL ingest/auth smoke passed. HMI build emitted a non-blocking 579.35 kB bundle warning.

The polling harness was interrupted by the deliberate API outage; final snapshots, complete replay and database/stream totals were retrieved after recovery. Correlation checks use frame IDs with tick suffixes. This demonstrates local synthetic behavior, not real-engine accuracy, production load or certification. RUL remains an experimental RULE_BASED_PROXY.

Evidence: [scenario summary](verification/2026-09-08/e2e-summary.json), [frame traces](verification/2026-09-08/trace-verification.json), [database totals](verification/2026-09-08/database-verification.json).

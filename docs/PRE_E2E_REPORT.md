# Pre-E2E follow-up

Local branch: integration/pre-e2e, based on merged main cc6f084. No remote push.

## Completed code and model checks

- Startup locates per-user Docker Desktop installations without relying on PATH.
- Compose uses project aerotwin-integration and separate named volumes. The older
  Downloads checkout uses project aerotwin-ai and remains untouched.
- Published ports are configurable. This laptop's ignored .env uses HMI 15173,
  API 14000, M1–M5 18001–18005, PostgreSQL 15432 and Redis 16379. CORS and the HMI
  API build URL match these ports. Default ports remain available on other machines.
- Compose selects M4 artifacts/v2 with 18 measured features. The registry reads
  feature order and producer version from metadata; missing temperature metadata
  returns HTTP 422. Legacy 16-feature v1 remains available.
- Calibration uses disjoint seeds and actual M1 → M2 → M4 processing. The 1,754
  held-out synthetic states achieved macro F1 1.0, with no normal physical-fault
  claims. Shared templates and threshold-derived labels limit what this proves;
  it does not establish real-engine performance. See the v2 model card/metrics.
- Python suites: M1 21, M2 18, M3 7, M4 28, M5 60, adapter 1: **135 passed**.
- Updated contract smoke: **2,419 schema checks passed**; normal NONE, oil-pressure
  OIL_PRESSURE_DEGRADATION, overheating OVERHEATING, vibration VIBRATION_MISFIRE,
  dropout quality suppression. These use real module code via TestClient.

## Docker verification

Docker Engine 29.7.2 and Compose 5.4.0 respond. Build and health verification is in progress.

## Remaining acceptance scope

Full five-scenario browser E2E, live refresh/reconnect and worker restart acceptance
remain separate. M5 is explicitly the experimental RULE_BASED_PROXY; trained RUL
accuracy is not claimed. Thresholds and units still require domain-owner review.

## Completed follow-up
The subsequent five-scenario Docker/browser verification is recorded in [E2E_REPORT.md](E2E_REPORT.md). Earlier pending status above is historical.

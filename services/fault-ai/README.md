# M4 — Fault Prediction & Explainable AI Service (SIH26-26054)

**Module 4:** Dual-model anomaly detection, 5-class fault classification, quality-aware decision fusion, TreeSHAP explainability, and M6 handoff.  
**Commitment:** Core MVP Demonstrator | **API Port:** `8004` | **Stream Group:** `m4-fault-ai`  

---

## ⚠️ Mandatory Hackathon Safety Disclaimers

> [!IMPORTANT]
> - **Hackathon Demonstrator Only**: This service uses synthetic telemetry and approved public datasets for SIH26-26054. It is strictly an experimental demonstrator.
> - **No Airworthiness Claim**: This system is not certified for aviation deployment, real UAV flight control, or safety-critical field operations.
> - **No Autonomous Control**: All predictions are advisory only. The system does not directly command or override engine actuators or flight computers.
> - **Separation of Metrics**: Measured demonstration metrics (e.g. synthetic test set F1 score) are internal benchmarks and do not constitute field-performance claims.

---

## 📦 Artifact & Source Control Policy

- **Source Fixtures (`artifacts/v1/*.json`)**: Small synthetic JSON datasets (`train_dataset.json`, `test_manifest.json`) are checked in for demo bootstrapping so the system runs out-of-the-box on a fresh clone.
- **Generated Binaries (`*.joblib`, `*.parquet`)**: Heavy model binaries and parquet files are excluded via `.gitignore`. Running `python -m training.train` builds and promotes versioned artifacts locally with SHA256 checksums recorded in the `/health/ready` manifest.

---

## 🚀 Quickstart Commands

### 1. Installation
```bash
cd services/fault-ai
pip install -e .[dev]
```

### 2. Run All Pytest Suite
```bash
python -m pytest tests/
```

### 3. Build Synthetic Dataset
Generates 5 scenario families (`NONE`, `OVERHEATING`, `OIL_PRESSURE_DEGRADATION`, `VIBRATION_MISFIRE`, `SENSOR_FAULT`) with a 70/15/15 `GroupShuffleSplit` by `missionId`:
```bash
python -m training.build_dataset
```

### 4. Train Models
Trains Isolation Forest and 5-class Fault Classifier with probability calibration:
```bash
python -m training.train
```

### 5. Evaluate Models & Generate Model Card
Evaluates models on held-out test missions and generates `metrics.json` and `model_card.md`:
```bash
python -m training.evaluate
```

### 6. Run FastAPI Service Locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

### 7. Run Redis Consumer Worker Locally
```bash
python -m app.worker
```

### 8. Run via Docker Compose (API + Redis Consumer Worker)
From the repository root:
```bash
docker compose up --build fault-ai fault-ai-worker
```

### 9. Verify M4 -> M6 Handoff
```bash
curl -X POST http://localhost:8004/predict \
  -H "Content-Type: application/json" \
  -d '{
    "engineId": "ENG-001",
    "missionId": "MSN-OILPRESS-001",
    "correlationId": "CORR-TEST-99",
    "stateTime": "2026-08-24T20:00:00Z",
    "producerVersion": "1.0.0",
    "load": 80.0,
    "margins": {"tempMarginC": 15.0, "pressureMarginKpa": 45.0, "vibrationMarginMmS": 2.0},
    "derivedFeatures": {"rollingMeanRpm": 2400.0, "rollingStdVibration": 0.2, "rateOfChangeOilTempCPerMin": 0.05, "sampleWindowSeconds": 30.0},
    "stateQuality": "GOOD"
  }'
```

---

## 🔌 API & Readiness Contracts

- **`GET /health/live`**: Process liveness probe.
- **`GET /health/ready`**: Model & feature pipeline readiness probe. Returns **HTTP 503** if model binary artifacts (`isolation_forest.joblib`, `xgboost_fault.json`) are absent or failed to load. Returns SHA256 checksum manifest when ready.
- **`POST /predict`**: Accepts `TwinState` frame or `TwinStateWindow`. Returns `FaultPrediction` with `faultType`, `confidence`, `anomalyScore`, dynamic TreeSHAP `contributors`, and `detectionDelayMs` (for labeled replay scenarios).

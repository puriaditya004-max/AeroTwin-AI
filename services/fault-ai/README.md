# M4 — Fault Prediction & Explainable AI Service (SIH26-26054)

**Module 4:** Anomaly detection, 5-class fault classification, quality-aware decision fusion, TreeSHAP explainability, and M6 handoff.  
**Commitment:** Core MVP Demonstrator | **Port:** `8004`  

---

## ⚠️ Mandatory Hackathon Safety Disclaimers

> [!IMPORTANT]
> - **Hackathon Demonstrator Only**: This service uses synthetic telemetry and approved public datasets for SIH26-26054. It is strictly an experimental demonstrator.
> - **No Airworthiness Claim**: This system is not certified for aviation deployment, real UAV flight control, or safety-critical field operations.
> - **No Autonomous Control**: All predictions are advisory only. The system does not directly command or override engine actuators or flight computers.
> - **Separation of Metrics**: Measured demonstration metrics (e.g. synthetic test set F1 score) are internal benchmarks and do not constitute field-performance claims.

---

## 🛠️ Stack

- **Language & Framework**: Python 3.12, FastAPI, Pydantic v2, Uvicorn
- **Machine Learning**: scikit-learn (`IsolationForest`), XGBoost / HistGradientBoostingClassifier, SHAP (`TreeExplainer`), Joblib
- **Data & Transport**: Pandas, NumPy, Redis Streams, HTTPX, Pytest

---

## 🚀 Quickstart Commands

### 1. Installation
```bash
cd services/fault-ai
pip install -e .[dev]
```

### 2. Build Synthetic Dataset
Generates 5 scenario families (`NONE`, `OVERHEATING`, `OIL_PRESSURE_DEGRADATION`, `VIBRATION_MISFIRE`, `SENSOR_FAULT`) with a 70/15/15 `GroupShuffleSplit` by `missionId`:
```bash
python -m training.build_dataset
```

### 3. Train Models
Trains Isolation Forest and 5-class Fault Classifier with probability calibration:
```bash
python -m training.train
```

### 4. Evaluate Models & Generate Model Card
Evaluates models on held-out test missions and generates `metrics.json` and `model_card.md`:
```bash
python -m training.evaluate
```

### 5. Run Unit & Integration Tests
```bash
pytest tests/
```

### 6. Run FastAPI Service Locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

### 7. Run via Docker Compose
From the repository root:
```bash
docker compose up --build fault-ai
```

---

## 🔌 API Contracts

- **Health Probes**:
  - `GET /health/live`: Process liveness check
  - `GET /health/ready`: Model & feature pipeline readiness check
- **Inference Endpoint**:
  - `POST /predict`: Accepts a `TwinState` frame or 30s `TwinStateWindow` payload. Returns a `FaultPrediction` contract object:
    ```json
    {
      "engineId": "ENG-001",
      "missionId": "MSN-OILPRESS-001",
      "correlationId": "CORR-9941",
      "predictionTime": "2026-08-24T20:00:00Z",
      "producerVersion": "1.0.0",
      "faultType": "OIL_PRESSURE_DEGRADATION",
      "confidence": 0.942,
      "anomalyScore": 0.815,
      "contributors": [
        { "feature": "pressureMarginKpa", "contribution": -0.81 },
        { "feature": "window_slope_pressureMarginKpa", "contribution": -0.39 }
      ],
      "detectionDelayMs": 350.0
    }
    ```

---

## 🛡️ Quality & Safety Rules

1. **State Quality Gate**: If telemetry `stateQuality` is `STALE` or `DEGRADED`, physical fault claims are suppressed (`faultType: NONE`, `confidence: 0.0`, `anomalyScore: 0.0`).
2. **Leakage Protection**: Feature fitting (imputation, scaling, rolling window statistics) occurs on TRAIN data only. Zero test data leakage across `missionId`.
3. **Idempotent M6 Handoff**: The background worker sends `X-Idempotency-Key: {correlationId}` headers with bounded exponential backoff retries when M6 is unavailable.

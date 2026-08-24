"""
M4 Fault AI - FastAPI Service Main Entrypoint

Structured JSON logging, Pydantic contracts validation, dynamic TreeSHAP explainability,
detection delay calculation, and quality-aware decision fusion.
"""

from datetime import datetime, timezone
import json
import logging
import time
from typing import Dict, Any, Union
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from app.contracts import TwinState, TwinStateWindow, FaultPrediction, FaultType, StateQuality
from models.classifier import LABEL_MAP
from models.registry import ModelRegistry

# Configure production structured JSON logger
logger = logging.getLogger("m4-fault-ai")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def log_prediction_event(
    missionId: str,
    engineId: str,
    correlationId: str,
    faultType: str,
    confidence: float,
    anomalyScore: float,
    latencyMs: float,
    producerVersion: str = "1.0.0",
    detectionDelayMs: Any = None
):
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "m4-fault-ai",
        "producerVersion": producerVersion,
        "engineId": engineId,
        "missionId": missionId,
        "correlationId": correlationId,
        "faultType": faultType,
        "confidence": round(confidence, 4),
        "anomalyScore": round(anomalyScore, 4),
        "latencyMs": round(latencyMs, 2),
        "detectionDelayMs": round(detectionDelayMs, 2) if detectionDelayMs is not None else None
    }
    logger.info(json.dumps(log_payload))


app = FastAPI(
    title="AeroTwin AI - M4 Fault AI Service",
    description="Dual-model anomaly detection, XGBoost fault classification, decision fusion & SHAP explainability.",
    version="1.0.0"
)

registry = ModelRegistry()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    manifest: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Load promoted model artifacts on startup."""
    registry.load_artifacts()


@app.get("/health/live", response_model=HealthResponse)
async def health_live():
    """Liveness probe confirming service process is active."""
    return HealthResponse(
        status="UP",
        service="m4-fault-ai",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        manifest=registry.get_manifest()
    )


@app.get("/health/ready", response_model=HealthResponse)
async def health_ready():
    """Readiness probe confirming model artifacts and pipelines are loaded."""
    if not registry.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Models or feature pipeline not loaded"
        )
    return HealthResponse(
        status="READY",
        service="m4-fault-ai",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        manifest=registry.get_manifest()
    )


@app.post("/predict", response_model=FaultPrediction)
async def predict_fault(payload: Union[TwinState, TwinStateWindow]):
    """
    Inference endpoint: accepts TwinState frame or 30s TwinStateWindow.
    Performs feature building, Isolation Forest anomaly scoring, FaultClassifier inference,
    TreeSHAP explanation matching predicted class, and quality-aware decision fusion.
    """
    start_time = time.perf_counter()

    if isinstance(payload, TwinStateWindow):
        if not payload.states:
            raise HTTPException(status_code=400, detail="Empty states list in TwinStateWindow")
        states = payload.states
        latest = states[-1]
        onset_timestamp = payload.faultOnsetTimestamp or latest.faultOnsetTimestamp
    else:
        states = [payload]
        latest = payload
        onset_timestamp = latest.faultOnsetTimestamp

    now_utc = datetime.now(timezone.utc)

    # Safety fallback for STALE or DEGRADED telemetry quality
    if latest.stateQuality in (StateQuality.STALE, StateQuality.DEGRADED):
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        prediction = FaultPrediction(
            engineId=latest.engineId,
            missionId=latest.missionId,
            correlationId=latest.correlationId,
            predictionTime=now_utc,
            producerVersion="1.0.0",
            faultType=FaultType.NONE,
            confidence=0.0,
            anomalyScore=0.0,
            contributors=[],
            detectionDelayMs=None
        )
        log_prediction_event(
            missionId=latest.missionId,
            engineId=latest.engineId,
            correlationId=latest.correlationId,
            faultType=FaultType.NONE.value,
            confidence=0.0,
            anomalyScore=0.0,
            latencyMs=latency_ms,
            producerVersion="1.0.0"
        )
        return prediction

    # 1. Extract Feature Vector
    feature_vec = registry.feature_pipeline.extract_from_window(states)

    # 2. Anomaly Engine Inference
    anomaly_score = float(registry.anomaly_engine.predict_anomaly_score(feature_vec.reshape(1, -1))[0])

    # 3. Fault Classifier Inference
    types, confs = registry.classifier.predict(feature_vec.reshape(1, -1))
    pred_type = types[0]
    pred_conf = float(confs[0])

    # 4. Dynamic TreeSHAP Explanation matched to predicted class
    target_class_idx = LABEL_MAP.get(pred_type.value, 0)
    top_contributors = registry.explainer.get_top_contributors(
        feature_vec,
        target_class_idx=target_class_idx,
        top_k=5
    )

    # 5. Quality-Aware Decision Fusion Policy
    prediction = registry.fusion_policy.fuse(
        latest_state=latest,
        anomaly_score=anomaly_score,
        predicted_type=pred_type,
        confidence=pred_conf,
        contributors=top_contributors
    )

    # 6. Detection Delay Calculation for labeled replay scenarios
    if prediction.faultType != FaultType.NONE and onset_timestamp is not None:
        if onset_timestamp.tzinfo is None:
            onset_timestamp = onset_timestamp.replace(tzinfo=timezone.utc)
        delay_ms = max(0.0, (now_utc - onset_timestamp).total_seconds() * 1000.0)
        prediction.detectionDelayMs = round(delay_ms, 2)

    latency_ms = (time.perf_counter() - start_time) * 1000.0

    # 7. Production Structured Logging
    log_prediction_event(
        missionId=prediction.missionId,
        engineId=prediction.engineId,
        correlationId=prediction.correlationId,
        faultType=prediction.faultType.value,
        confidence=prediction.confidence,
        anomalyScore=prediction.anomalyScore,
        latencyMs=latency_ms,
        producerVersion=prediction.producerVersion,
        detectionDelayMs=prediction.detectionDelayMs
    )

    return prediction


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8004, reload=True)

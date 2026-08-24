"""
M4 Fault AI - FastAPI Service Main Entrypoint
"""

from datetime import datetime, timezone
import os
from typing import Dict, Any, Union
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from app.contracts import TwinState, TwinStateWindow, FaultPrediction, FaultType, StateQuality
from models.registry import ModelRegistry

app = FastAPI(
    title="AeroTwin AI - M4 Fault AI Service",
    description="Dual-model anomaly detection, XGBoost fault classification, decision fusion & SHAP explainability.",
    version="1.0.0"
)

# Global model registry instance
registry = ModelRegistry()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    manifest: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Load model artifacts on application startup."""
    registry.load_artifacts()


@app.get("/health/live", response_model=HealthResponse)
async def health_live():
    """Liveness probe to confirm service process is active."""
    return HealthResponse(
        status="UP",
        service="m4-fault-ai",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        manifest=registry.get_manifest()
    )


@app.get("/health/ready", response_model=HealthResponse)
async def health_ready():
    """Readiness probe to confirm models and pipelines are loaded."""
    if not registry.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Models or pipeline not loaded"
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
    Accepts a single TwinState frame or a TwinStateWindow (30s rolling),
    runs feature extraction, dual inference (Isolation Forest + XGBoost),
    quality-aware decision fusion, and SHAP explainability.
    """
    # Extract latest state and window list
    if isinstance(payload, TwinStateWindow):
        if not payload.states:
            raise HTTPException(status_code=400, detail="Empty states list in TwinStateWindow")
        states = payload.states
        latest = states[-1]
    else:
        states = [payload]
        latest = payload

    # Safety fallback rule for degraded/stale state quality
    if latest.stateQuality in (StateQuality.STALE, StateQuality.DEGRADED):
        return FaultPrediction(
            engineId=latest.engineId,
            missionId=latest.missionId,
            correlationId=latest.correlationId,
            predictionTime=datetime.now(timezone.utc),
            producerVersion="1.0.0",
            faultType=FaultType.NONE,
            confidence=0.0,
            anomalyScore=0.0,
            contributors=[],
            detectionDelayMs=None
        )

    # 1. Feature Extraction
    feature_vec = registry.feature_pipeline.extract_from_window(states)

    # 2. Anomaly Engine Inference
    anomaly_score = float(registry.anomaly_engine.predict_anomaly_score(feature_vec.reshape(1, -1))[0])

    # 3. XGBoost Classifier Inference
    types, confs = registry.classifier.predict(feature_vec.reshape(1, -1))
    pred_type = types[0]
    pred_conf = float(confs[0])

    # 4. SHAP Explanation
    top_contributors = registry.explainer.get_top_contributors(
        feature_vec,
        class_idx=0 if pred_type == FaultType.NONE else 1,
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

    return prediction


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8004, reload=True)

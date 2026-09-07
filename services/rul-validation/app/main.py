from fastapi import FastAPI, HTTPException
from .rul_contract import build_rul_estimate
from .predictor import RULPredictor
from .schemas import (
    M3M4HealthData,
    RULPredictionRequest,
    RULPredictionResponse,
)
from .risk_logic import (
    calculate_health_status,
    calculate_risk_level,
    calculate_trend,
)
from .prediction_history import PredictionHistory


# =========================================================
# M5 - RUL Prediction API
# =========================================================

app = FastAPI(
    title="AeroTwin-AI M5 - RUL Prediction Service",
    description=(
        "Remaining Useful Life prediction API "
        "with uncertainty, risk, health and trend analysis"
    ),
    version="1.5.0",
)


# =========================================================
# Load model once when service starts
# =========================================================

try:
    predictor = RULPredictor()
except Exception as exc:
    predictor = None
    model_load_error = str(exc)


# =========================================================
# Prediction History Store
# =========================================================

prediction_histories: dict[str, PredictionHistory] = {}


# =========================================================
# Get/Create History for Engine
# =========================================================

def get_prediction_history(engine_id: str) -> PredictionHistory:
    """
    Return prediction history for a specific engine.

    A separate in-memory history is maintained for each engine.
    """

    if engine_id not in prediction_histories:
        prediction_histories[engine_id] = PredictionHistory(
            max_size=20
        )

    return prediction_histories[engine_id]


# =========================================================
# Health Endpoint
# =========================================================

@app.get("/health")
def health_check():
    """
    Check whether the RUL service is ready.
    """

    if predictor is None:
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "model_loaded": False, "error": model_load_error})

    return {
        "status": "healthy",
        "model_loaded": True,
        "model_source": predictor.model_source,
    }


# =========================================================
# Helper Function
# =========================================================

def build_prediction_response(
    result: dict,
    health_index: float,
    previous_rul: float | None = None,
) -> RULPredictionResponse:
    """
    Build the complete M5 prediction response.
    """

    predicted_rul = result["predicted_rul"]

    # -----------------------------------------------------
    # Risk level
    # -----------------------------------------------------

    risk_level = calculate_risk_level(
        predicted_rul
    )

    # -----------------------------------------------------
    # Health status
    # -----------------------------------------------------

    health_status = calculate_health_status(
        health_index
    )

    # -----------------------------------------------------
    # RUL trend
    # -----------------------------------------------------

    if previous_rul is None:
        trend = "STABLE"
    else:
        trend = calculate_trend(
            current_rul=predicted_rul,
            previous_rul=previous_rul,
        )

    # -----------------------------------------------------
    # Final response
    # -----------------------------------------------------

    return RULPredictionResponse(
        predicted_rul=result["predicted_rul"],
        lower_bound=result["lower_bound"],
        upper_bound=result["upper_bound"],
        uncertainty_margin=result["uncertainty_margin"],
        risk_level=risk_level,
        health_status=health_status,
        trend=trend,
        unit=result["unit"],
    )


# =========================================================
# Direct M5 Prediction Endpoint
# =========================================================

@app.post(
    "/predict-rul",
    response_model=RULPredictionResponse,
)
def predict_rul(
    request: RULPredictionRequest,
):
    """
    Predict RUL using sensor values.

    This endpoint does not have engine_id, so prediction
    history is not stored here.
    """

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="RUL model is not loaded.",
        )

    try:

        result = predictor.predict_with_uncertainty(
            temperature=request.temperature,
            vibration=request.vibration,
            pressure=request.pressure,
            rpm=request.rpm,
            load=request.load,
            health_index=request.health_index,
        )

        return build_prediction_response(
            result=result,
            health_index=request.health_index,
            previous_rul=request.previous_rul,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}",
        ) from exc


# =========================================================
# M3/M4 → M5 Prediction Endpoint
# =========================================================

@app.post(
    "/predict-from-health-data",
    response_model=RULPredictionResponse,
)
def predict_from_health_data(
    request: M3M4HealthData,
):
    """
    Receive complete health/sensor data from M3/M4
    and generate M5 RUL prediction.

    Prediction is stored in engine-specific history.
    """

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="RUL model is not loaded.",
        )

    try:

        # -------------------------------------------------
        # Generate prediction
        # -------------------------------------------------

        result = predictor.predict_with_uncertainty(
            temperature=request.temperature,
            vibration=request.vibration,
            pressure=request.pressure,
            rpm=request.rpm,
            load=request.load,
            health_index=request.health_index,
        )

        # -------------------------------------------------
        # Get engine-specific history
        # -------------------------------------------------

        history = get_prediction_history(
            request.engine_id
        )

        # -------------------------------------------------
        # Get previous prediction from history
        # -------------------------------------------------

        previous_prediction = history.get_latest()

        previous_rul = (
            previous_prediction["predicted_rul"]
            if previous_prediction is not None
            else None
        )

        # -------------------------------------------------
        # Calculate risk and health
        # -------------------------------------------------

        risk_level = calculate_risk_level(
            result["predicted_rul"]
        )

        health_status = calculate_health_status(
            request.health_index
        )

        # -------------------------------------------------
        # Store prediction in history
        # -------------------------------------------------

        history.add_prediction(
            predicted_rul=result["predicted_rul"],
            lower_bound=result["lower_bound"],
            upper_bound=result["upper_bound"],
            risk_level=risk_level,
            health_status=health_status,
        )

        # -------------------------------------------------
        # Calculate reliable trend from history
        # -------------------------------------------------

        trend = history.calculate_trend()

        # -------------------------------------------------
        # Build final response
        # -------------------------------------------------

        return RULPredictionResponse(
            predicted_rul=result["predicted_rul"],
            lower_bound=result["lower_bound"],
            upper_bound=result["upper_bound"],
            uncertainty_margin=result["uncertainty_margin"],
            risk_level=risk_level,
            health_status=health_status,
            trend=trend,
            unit=result["unit"],
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}",
        ) from exc


# =========================================================
# Prediction History Endpoint
# =========================================================

@app.get(
    "/history/{engine_id}"
)
def get_engine_history(
    engine_id: str,
):
    """
    Return prediction history and reliable trend
    for a specific engine.
    """

    if not engine_id.strip():
        raise HTTPException(
            status_code=400,
            detail="engine_id cannot be empty.",
        )

    history = get_prediction_history(
        engine_id
    )

    return {
        "engine_id": engine_id,
        "history": history.get_history(),
        "history_count": history.size(),
        "trend": history.calculate_trend(),
    }


# =========================================================
# Clear Prediction History Endpoint
# =========================================================

@app.delete(
    "/history/{engine_id}"
)
def clear_engine_history(
    engine_id: str,
):
    """
    Clear prediction history for a specific engine.
    """

    if not engine_id.strip():
        raise HTTPException(
            status_code=400,
            detail="engine_id cannot be empty.",
        )

    history = get_prediction_history(
        engine_id
    )

    history.clear()

    return {
        "engine_id": engine_id,
        "history": [],
        "history_count": 0,
        "trend": "STABLE",
        "message": "Prediction history cleared.",
    }


from pydantic import BaseModel, model_validator
from contracts import TwinState, HealthSnapshot, RulEstimate, RulBasis


class CanonicalRulRequest(BaseModel):
    state: TwinState
    health: HealthSnapshot

    @model_validator(mode="after")
    def same_event(self):
        for key in ("engineId", "missionId", "correlationId"):
            if getattr(self.state, key) != getattr(self.health, key):
                raise ValueError(f"State/health {key} mismatch")
        if self.state.stateTime != self.health.snapshotTime:
            raise ValueError("State/health timestamps mismatch")
        return self


@app.post("/estimate", response_model=RulEstimate, response_model_exclude_none=True)
def canonical_estimate(request: CanonicalRulRequest):
    if predictor is None:
        raise HTTPException(status_code=503, detail="RUL model is not loaded")
    state, health = request.state, request.health
    sensors = (state.model_extra or {}).get("sensors")
    required = ("oilTempC", "vibrationMmS", "oilPressureKpa", "rpm")
    if not isinstance(sensors, dict) or any(key not in sensors for key in required):
        raise HTTPException(status_code=422, detail="M2 measured sensors metadata required")
    # Keep original model's feature order; measurements use canonical units.
    result = predictor.predict_with_uncertainty(
        temperature=sensors["oilTempC"], vibration=sensors["vibrationMmS"],
        pressure=sensors["oilPressureKpa"], rpm=sensors["rpm"],
        load=state.load, health_index=health.healthScore / 100,
    )
    proxy = predictor.model_source.startswith("experimental:")
    return build_rul_estimate(
        engine_id=state.engineId, mission_id=state.missionId,
        correlation_id=state.correlationId, estimate_time=state.stateTime,
        predicted_rul=result["predicted_rul"], lower_bound=result["lower_bound"],
        upper_bound=result["upper_bound"], trend=health.trend,
        basis=RulBasis.RULE_BASED_PROXY if proxy else RulBasis.ML_REGRESSION,
        producer_version=predictor.model_source,
    )

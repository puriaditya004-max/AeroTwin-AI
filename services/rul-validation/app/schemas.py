from typing import Literal

from pydantic import BaseModel, Field


# =========================================================
# M3/M4 → M5 Input Contract
# =========================================================

class M3M4HealthData(BaseModel):
    """
    Contract for health/sensor data received from M3/M4.
    """

    engine_id: str = Field(
        ...,
        min_length=1,
        description="Unique engine identifier",
    )

    cycle: int = Field(
        ...,
        ge=0,
        description="Current operating cycle",
    )

    temperature: float = Field(
        ...,
        description="Engine temperature",
    )

    vibration: float = Field(
        ...,
        ge=0.0,
        description="Engine vibration",
    )

    pressure: float = Field(
        ...,
        ge=0.0,
        description="Engine pressure",
    )

    rpm: float = Field(
        ...,
        ge=0.0,
        description="Engine RPM",
    )

    load: float = Field(
        ...,
        ge=0.0,
        description="Engine load",
    )

    health_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Engine health index",
    )

    previous_rul: float | None = Field(
        default=None,
        ge=0.0,
        description="Previous RUL prediction for trend analysis",
    )


# =========================================================
# M5 RUL Prediction Request Contract
# =========================================================

class RULPredictionRequest(BaseModel):
    """
    Direct M5 prediction request.

    engine_id is optional for backward compatibility.
    If it is not supplied, the API can use a default
    engine history.
    """

    engine_id: str = Field(
        default="DEFAULT-ENGINE",
        min_length=1,
        description="Unique engine identifier",
    )

    temperature: float = Field(
        ...,
        description="Engine temperature",
    )

    vibration: float = Field(
        ...,
        ge=0.0,
        description="Engine vibration",
    )

    pressure: float = Field(
        ...,
        ge=0.0,
        description="Engine pressure",
    )

    rpm: float = Field(
        ...,
        ge=0.0,
        description="Engine RPM",
    )

    load: float = Field(
        ...,
        ge=0.0,
        description="Engine load",
    )

    health_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Engine health index",
    )

    previous_rul: float | None = Field(
        default=None,
        ge=0.0,
        description="Previous RUL prediction for trend analysis",
    )


# =========================================================
# M5 RUL Prediction Response Contract
# =========================================================

class RULPredictionResponse(BaseModel):
    """
    Complete M5 prediction response.
    """

    predicted_rul: float = Field(
        ...,
        ge=0.0,
        description="Predicted remaining useful life",
    )

    lower_bound: float = Field(
        ...,
        ge=0.0,
        description="Lower uncertainty bound for RUL",
    )

    upper_bound: float = Field(
        ...,
        ge=0.0,
        description="Upper uncertainty bound for RUL",
    )

    uncertainty_margin: float = Field(
        ...,
        ge=0.0,
        description="Experimental uncertainty margin",
    )

    risk_level: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ] = Field(
        ...,
        description="RUL-based risk level",
    )

    health_status: Literal[
        "GOOD",
        "DEGRADED",
        "POOR",
        "CRITICAL",
    ] = Field(
        ...,
        description="Health-index based status",
    )

    trend: Literal[
        "IMPROVING",
        "DEGRADING",
        "STABLE",
    ] = Field(
        ...,
        description="RUL trend",
    )

    unit: str = Field(
        default="cycles",
        description="RUL unit",
    )

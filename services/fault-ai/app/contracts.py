"""
M4 Fault AI - Pydantic Contracts

Canonical source of truth for TwinState, FaultPrediction, and domain models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class StateQuality(str, Enum):
    GOOD = "GOOD"
    STALE = "STALE"
    DEGRADED = "DEGRADED"


class Margins(BaseModel):
    tempMarginC: float
    pressureMarginKpa: float
    vibrationMarginMmS: float


class DerivedFeatures(BaseModel):
    rollingMeanRpm: float
    rollingStdVibration: float
    rateOfChangeOilTempCPerMin: float
    sampleWindowSeconds: float = Field(default=30.0, ge=0)


class TwinState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    engineId: str
    missionId: str
    correlationId: str
    stateTime: datetime
    producerVersion: str = "1.0.0"
    load: float = Field(ge=0, le=100)
    margins: Margins
    derivedFeatures: DerivedFeatures
    stateQuality: StateQuality
    syncLagMs: Optional[float] = Field(default=None, ge=0)
    faultOnsetTimestamp: Optional[datetime] = Field(default=None, description="Preset onset time for detection delay calculation in labeled replay")


class TwinStateWindow(BaseModel):
    engineId: str
    missionId: str
    states: List[TwinState]
    faultOnsetTimestamp: Optional[datetime] = None


class FaultType(str, Enum):
    NONE = "NONE"
    OVERHEATING = "OVERHEATING"
    OIL_PRESSURE_DEGRADATION = "OIL_PRESSURE_DEGRADATION"
    VIBRATION_MISFIRE = "VIBRATION_MISFIRE"
    SENSOR_FAULT = "SENSOR_FAULT"


class Contributor(BaseModel):
    feature: str
    contribution: float


class FaultPrediction(BaseModel):
    engineId: str
    missionId: str
    correlationId: str
    predictionTime: datetime
    producerVersion: str = "1.0.0"
    faultType: FaultType
    confidence: float = Field(ge=0, le=1)
    anomalyScore: float = Field(ge=0, le=1)
    contributors: List[Contributor] = Field(default_factory=list)
    detectionDelayMs: Optional[float] = Field(default=None, ge=0)

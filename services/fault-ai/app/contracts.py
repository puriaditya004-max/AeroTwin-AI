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
    model_config = ConfigDict(extra="allow")
    rollingMeanRpm: float
    rollingStdVibration: float
    rateOfChangeOilTempCPerMin: float
    sampleWindowSeconds: float = Field(default=30.0, ge=0)
    oilPressureDeviationKpa: Optional[float] = None
    oilTempDeviationC: Optional[float] = None
    coolantTempDeviationC: Optional[float] = None
    vibrationDeviationMmS: Optional[float] = None
    expectedOilTempC: Optional[float] = None
    expectedCoolantTempC: Optional[float] = None
    expectedOilPressureKpa: Optional[float] = None
    expectedVibrationMmS: Optional[float] = None
    reasonCodes: list[str] = Field(default_factory=list)


class TwinState(BaseModel):
    model_config = ConfigDict(extra="allow")

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


class FaultSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


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
    componentId: Optional[str] = None
    subsystem: Optional[str] = None
    severity: Optional[FaultSeverity] = None
    evidence: List[str] = Field(default_factory=list)
    recommendedAction: Optional[str] = None
    alternativePossibilities: List[str] = Field(default_factory=list)
    requiresHumanConfirmation: Optional[bool] = None
    operatingConditionOutOfRange: Optional[bool] = None

"""
AeroTwin AI - Shared contract models (Pydantic v2)

Canonical source of truth is /packages/schemas/json-schema/*.schema.json.
These Pydantic models mirror those schemas for use in M1-M5 Python services.
Do not edit a contract here without updating the matching JSON Schema and
writing a short ADR in /docs/decisions/.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# TelemetryFrame  (Producer: M1 -> Consumer: M2)
# ---------------------------------------------------------------------------

class QualityFlag(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    DROPOUT = "DROPOUT"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"


class Sensors(BaseModel):
    rpm: float = Field(ge=0, le=4000)
    oilPressureKpa: float = Field(ge=0, le=1000)
    oilTempC: float = Field(ge=-40, le=200)
    coolantTempC: float = Field(ge=-40, le=200)
    vibrationMmS: float = Field(ge=0, le=50)
    fuelFlowLph: float = Field(ge=0, le=100)
    throttlePct: float = Field(ge=0, le=100)
    altitudeM: float = Field(ge=0, le=12000)
    ambientTempC: float = Field(ge=-60, le=60)
    ambientPressureKpa: float = Field(ge=10, le=110)


class TelemetryFrame(BaseModel):
    engineId: str
    missionId: str
    correlationId: str
    timestamp: datetime
    producerVersion: str
    sensors: Sensors
    qualityFlag: QualityFlag
    scenarioId: Optional[str] = None


# ---------------------------------------------------------------------------
# TwinState  (Producer: M2 -> Consumers: M3, M4, M5)
# ---------------------------------------------------------------------------

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
    sampleWindowSeconds: float = Field(ge=0)


class TwinState(BaseModel):
    engineId: str
    missionId: str
    correlationId: str
    stateTime: datetime
    producerVersion: str
    load: float = Field(ge=0, le=100)
    margins: Margins
    derivedFeatures: DerivedFeatures
    stateQuality: StateQuality
    syncLagMs: Optional[float] = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# HealthSnapshot  (Producer: M3 -> Consumers: M5, M6)
# ---------------------------------------------------------------------------

class Trend(str, Enum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DEGRADING = "DEGRADING"


class SubScores(BaseModel):
    temperature: Optional[float] = Field(default=None, ge=0, le=100)
    pressure: Optional[float] = Field(default=None, ge=0, le=100)
    vibration: Optional[float] = Field(default=None, ge=0, le=100)
    load: Optional[float] = Field(default=None, ge=0, le=100)


class HealthSnapshot(BaseModel):
    engineId: str
    missionId: str
    correlationId: str
    snapshotTime: datetime
    producerVersion: str
    healthScore: float = Field(ge=0, le=100)
    trend: Trend
    subScores: Optional[SubScores] = None
    violatedRules: list[str]
    reasonCodes: list[str]
    ruleVersion: str
    dataQualityIssue: bool = False


# ---------------------------------------------------------------------------
# FaultPrediction  (Producer: M4 -> Consumers: M5, M6)
# ---------------------------------------------------------------------------

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
    producerVersion: str
    faultType: FaultType
    confidence: float = Field(ge=0, le=1)
    anomalyScore: float = Field(ge=0, le=1)
    contributors: list[Contributor]
    detectionDelayMs: Optional[float] = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# RulEstimate  (Producer: M5 -> Consumer: M6)
# ---------------------------------------------------------------------------

class RulBasis(str, Enum):
    ML_REGRESSION = "ML_REGRESSION"
    RULE_BASED_PROXY = "RULE_BASED_PROXY"


class RulEstimate(BaseModel):
    engineId: str
    missionId: str
    correlationId: str
    estimateTime: datetime
    producerVersion: str
    cycles: float = Field(ge=0)
    lowerBound: float = Field(ge=0)
    upperBound: float = Field(ge=0)
    trend: Trend
    experimental: bool = True
    basis: Optional[RulBasis] = None


# ---------------------------------------------------------------------------
# MissionAdvisory  (Producer: M6 -> Consumer: Operator HMI)
# ---------------------------------------------------------------------------

class Risk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Action(str, Enum):
    CONTINUE = "CONTINUE"
    REDUCE_LOAD = "REDUCE_LOAD"
    INSPECT = "INSPECT"


class ContributingSignals(BaseModel):
    healthScore: Optional[float] = None
    faultType: Optional[str] = None
    faultConfidence: Optional[float] = None
    rulCycles: Optional[float] = None


class SourceVersions(BaseModel):
    healthSnapshotVersion: Optional[str] = None
    faultPredictionVersion: Optional[str] = None
    rulEstimateVersion: Optional[str] = None


class MissionAdvisory(BaseModel):
    engineId: str
    missionId: str
    correlationId: str
    advisoryTime: datetime
    producerVersion: str
    risk: Risk
    action: Action
    explanation: str
    inspectionRequired: bool
    contributingSignals: Optional[ContributingSignals] = None
    sourceVersions: Optional[SourceVersions] = None

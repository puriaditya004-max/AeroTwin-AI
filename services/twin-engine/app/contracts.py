"""
M2 contract boundary.

These models intentionally mirror packages/schemas/python/contracts.py so M2 can
run as an isolated Docker service without changing the shared contracts.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class QualityFlag(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    DROPOUT = "DROPOUT"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"


class SensorQualityCode(str, Enum):
    OK = "OK"
    MISSING = "MISSING"
    STALE = "STALE"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    DEGRADED = "DEGRADED"


class SensorQuality(BaseModel):
    status: SensorQualityCode
    reason: Optional[str] = None


class Sensors(BaseModel):
    model_config = ConfigDict(extra="allow")

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
    chtCylindersC: Optional[list[float]] = None
    egtCylindersC: Optional[list[float]] = None
    alternatorVoltageV: Optional[float] = Field(default=None, ge=0, le=40)
    alternatorCurrentA: Optional[float] = Field(default=None, ge=-50, le=150)
    batteryVoltageV: Optional[float] = Field(default=None, ge=0, le=40)
    injectionTimingDeg: Optional[float] = Field(default=None, ge=-60, le=60)
    sensorQuality: Optional[dict[str, SensorQuality]] = None


class TelemetryFrame(BaseModel):
    model_config = ConfigDict(extra="allow")

    schemaVersion: str = "1.0.0"
    engineId: str
    missionId: str
    frameId: Optional[str] = None
    correlationId: str
    timestamp: datetime
    ingestTimestamp: Optional[datetime] = None
    producerVersion: str
    sensors: Sensors
    qualityFlag: QualityFlag
    scenarioId: Optional[str] = None


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
    sampleWindowSeconds: float = Field(ge=0)
    featureVersion: str = "m2-features@2.0.0"
    chtMaxC: Optional[float] = None
    chtMeanC: Optional[float] = None
    chtSpreadC: Optional[float] = None
    chtSlopeCPerMin: Optional[float] = None
    egtMaxC: Optional[float] = None
    egtMeanC: Optional[float] = None
    egtSpreadC: Optional[float] = None
    egtSlopeCPerMin: Optional[float] = None
    oilPressureDeviationKpa: Optional[float] = None
    fuelFlowDeviationLph: Optional[float] = None
    injectionTimingDeviationDeg: Optional[float] = None
    alternatorVoltageMarginV: Optional[float] = None
    batteryVoltageMarginV: Optional[float] = None
    vibrationRollingMeanMmS: Optional[float] = None
    vibrationSlopeMmSPerMin: Optional[float] = None
    vibrationPeakMmS: Optional[float] = None
    missingSensorRatio: float = Field(default=0.0, ge=0, le=1)
    invalidSensorRatio: float = Field(default=0.0, ge=0, le=1)
    stateConfidence: float = Field(default=1.0, ge=0, le=1)
    reasonCodes: list[str] = Field(default_factory=list)


class TwinState(BaseModel):
    model_config = ConfigDict(extra="allow")

    schemaVersion: str = "1.0.0"
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

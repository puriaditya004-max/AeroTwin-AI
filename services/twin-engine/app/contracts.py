"""
M2 contract boundary.

These models intentionally mirror packages/schemas/python/contracts.py so M2 can
run as an isolated Docker service without changing the shared contracts.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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

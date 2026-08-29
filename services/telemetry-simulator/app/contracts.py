"""
M1 contract boundary.

These models mirror packages/schemas/python/contracts.py so the simulator can
run as an isolated Docker service without editing shared contracts.
Canonical source: packages/schemas/json-schema/TelemetryFrame.schema.json.
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

from datetime import datetime

from pydantic import BaseModel


class SensorData(BaseModel):
    rpm: float
    temperature_c: float
    oil_pressure_psi: float
    vibration_g: float
    fuel_flow_lph: float
    throttle_pct: float
    altitude_m: float
    ambient_temperature_c: float


class TelemetryFrame(BaseModel):
    engineId: str
    missionId: str
    timestamp: datetime
    sensors: SensorData
    qualityFlag: str = "GOOD"
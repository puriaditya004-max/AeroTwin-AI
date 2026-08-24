from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class StreamSettings(BaseModel):
    input: str
    output: str
    group: str
    consumer: str


class SyncSettings(BaseModel):
    primaryWindowSeconds: int
    maxWindowSamples: int
    reorderToleranceMs: int
    staleAfterMs: int
    idempotencyTtl: int


class EstimatorSettings(BaseModel):
    maxRpm: float
    maxFuelFlowLph: float
    tempLimitC: float
    vibrationLimitMmS: float
    baseOilPressureMinKpa: float
    loadOilPressureSlopeKpa: float
    loadWeights: dict[str, float]


class ServiceSettings(BaseModel):
    name: str
    version: str
    port: int


class Settings(BaseModel):
    service: ServiceSettings
    streams: StreamSettings
    sync: SyncSettings
    estimator: EstimatorSettings
    redisUrl: str = "redis://localhost:6379/0"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache
def get_settings() -> Settings:
    config_path = Path(os.getenv("M2_CONFIG_PATH", "configs/m2.yaml"))
    raw = _load_yaml(config_path)
    raw["redisUrl"] = os.getenv("REDIS_URL", raw.get("redisUrl", "redis://localhost:6379/0"))
    raw["streams"]["input"] = os.getenv("M2_INPUT_STREAM", raw["streams"]["input"])
    raw["streams"]["output"] = os.getenv("M2_OUTPUT_STREAM", raw["streams"]["output"])
    raw["streams"]["group"] = os.getenv("M2_CONSUMER_GROUP", raw["streams"]["group"])
    raw["streams"]["consumer"] = os.getenv("M2_CONSUMER_NAME", raw["streams"]["consumer"])
    return Settings.model_validate(raw)

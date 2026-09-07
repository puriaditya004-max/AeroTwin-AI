from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


SERVICE_ROOT = Path(__file__).resolve().parents[1]


class ServiceSettings(BaseModel):
    name: str
    version: str
    port: int
    producerVersion: str
    schemaVersion: str = "2.0.0"


class StreamSettings(BaseModel):
    output: str
    field: str = "payload"


class PublishSettings(BaseModel):
    defaultRateHz: float = Field(gt=0)
    replayEpoch: str
    maxRetryAttempts: int = Field(ge=1)
    initialBackoffMs: int = Field(ge=0)
    maxBackoffMs: int = Field(ge=0)
    backoffMultiplier: float = Field(gt=1)
    leaseTtlSeconds: int = Field(ge=1, default=5)


class QualityRates(BaseModel):
    dropoutRate: float = Field(ge=0, le=1, default=0.0)
    dropoutFlagRate: float = Field(ge=0, le=1, default=0.0)
    duplicateRate: float = Field(ge=0, le=1, default=0.0)
    outOfOrderRate: float = Field(ge=0, le=1, default=0.0)
    outOfOrderShiftMs: int = Field(ge=0, default=1500)
    degradedRate: float = Field(ge=0, le=1, default=0.0)


class Settings(BaseModel):
    service: ServiceSettings
    streams: StreamSettings
    publish: PublishSettings
    quality: QualityRates
    scenarios: dict[str, str]
    redisUrl: str = "redis://localhost:6379/0"
    enablePublisher: bool = True
    configDir: Path = SERVICE_ROOT / "configs"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected mapping in {path}")
    return loaded


def load_yaml(path: Path) -> dict[str, Any]:
    return _load_yaml(path)


@lru_cache
def get_settings() -> Settings:
    config_path = Path(os.getenv("M1_CONFIG_PATH", SERVICE_ROOT / "configs" / "m1.yaml"))
    raw = _load_yaml(config_path)
    raw["redisUrl"] = os.getenv("REDIS_URL", raw.get("redisUrl", "redis://localhost:6379/0"))
    raw["streams"]["output"] = os.getenv("M1_OUTPUT_STREAM", raw["streams"]["output"])
    raw["enablePublisher"] = os.getenv("M1_ENABLE_PUBLISHER", "true").lower() in {"1", "true", "yes"}
    if os.getenv("M1_PRODUCER_VERSION"):
        raw["service"]["producerVersion"] = os.getenv("M1_PRODUCER_VERSION")
    settings = Settings.model_validate(raw)
    settings.configDir = config_path.parent
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()

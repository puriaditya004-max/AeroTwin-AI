from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import random

from app.contracts import QualityFlag, SensorQuality, SensorQualityCode, Sensors, TelemetryFrame
from app.settings import QualityRates
from simulation.noise import apply_jitter, apply_quality_decision, clamp_sensor_map, decide_quality_event
from simulation.seed import rng_from_seed


REQUIRED_SENSORS = (
    "rpm",
    "oilPressureKpa",
    "oilTempC",
    "coolantTempC",
    "vibrationMmS",
    "fuelFlowLph",
    "throttlePct",
    "altitudeM",
    "ambientTempC",
    "ambientPressureKpa",
)


def _parse_epoch(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _linear(start: float, end: float, progress: float) -> float:
    progress = max(0.0, min(1.0, progress))
    return start + (end - start) * progress


def _fault_progress(elapsed_s: float, inject_after_s: float, over_s: float) -> float:
    if elapsed_s < inject_after_s:
        return 0.0
    if over_s <= 0:
        return 1.0
    return (elapsed_s - inject_after_s) / over_s


def _apply_mode(mode: dict[str, Any], elapsed_s: float, inject_after_s: float, rng: random.Random) -> float:
    kind = str(mode.get("mode", "hold"))
    if kind == "linear":
        over_s = float(mode.get("overSeconds", 1.0))
        progress = _fault_progress(elapsed_s, inject_after_s, over_s)
        return _linear(float(mode["from"]), float(mode["to"]), progress)
    if kind == "spike":
        base = float(mode.get("base", 0.0))
        if elapsed_s < inject_after_s:
            return base
        period = max(float(mode.get("periodSeconds", 10.0)), 0.001)
        width = float(mode.get("widthSeconds", 1.0))
        phase = (elapsed_s - inject_after_s) % period
        if phase < width:
            return float(mode.get("spike", base))
        return base
    if kind == "hold":
        return float(mode.get("value", 0.0))
    raise ValueError(f"Unsupported sensor mode {kind!r}")


class EngineModel:
    """YAML-driven synthetic envelope. Not real engine physics."""

    def __init__(self, scenario: dict[str, Any], *, producer_version: str, schema_version: str, replay_epoch: str):
        self.scenario = scenario
        self.producer_version = producer_version
        self.schema_version = schema_version
        self.replay_epoch = _parse_epoch(replay_epoch)
        self.scenario_id = str(scenario["id"])
        self.engine_id = str(scenario.get("engineId", "ENG-001"))
        self.duration_s = float(scenario.get("durationSeconds", 120))
        self.rate_hz = float(scenario.get("publishRateHz", 1.0))
        self.inject_after_s = float(scenario.get("fault", {}).get("injectAfterSeconds", 0.0))
        self.nominal: dict[str, Any] = scenario.get("nominal", {})
        self.fault_sensors: dict[str, Any] = scenario.get("fault", {}).get("sensors", {})
        quality_raw = scenario.get("quality", {})
        self.quality = QualityRates.model_validate(quality_raw) if quality_raw else QualityRates()

    def tick_count(self) -> int:
        return max(1, int(round(self.duration_s * self.rate_hz)))

    def elapsed_for_tick(self, tick: int) -> float:
        return tick / self.rate_hz

    def is_complete(self, tick: int) -> bool:
        return tick >= self.tick_count()

    def _nominal_value(self, name: str, spec: Any, rng: random.Random) -> Any:
        if isinstance(spec, dict) and "mean" in spec:
            return apply_jitter(float(spec["mean"]), float(spec.get("jitter", 0.0)), rng)
        if isinstance(spec, dict) and "values" in spec:
            values = []
            for item in spec["values"]:
                if isinstance(item, dict):
                    values.append(apply_jitter(float(item["mean"]), float(item.get("jitter", 0.0)), rng))
                else:
                    values.append(float(item))
            return values
        if isinstance(spec, (int, float)):
            return float(spec)
        if isinstance(spec, list):
            return [float(item) for item in spec]
        return spec

    def generate_sensors(self, tick: int, rng: random.Random) -> dict[str, Any]:
        elapsed_s = self.elapsed_for_tick(tick)
        sensors: dict[str, Any] = {}
        for name, spec in self.nominal.items():
            sensors[name] = self._nominal_value(name, spec, rng)
        if elapsed_s >= self.inject_after_s:
            for name, mode in self.fault_sensors.items():
                sensors[name] = _apply_mode(mode, elapsed_s, self.inject_after_s, rng)
        return clamp_sensor_map(sensors)

    def build_frame(
        self,
        tick: int,
        rng: random.Random,
        *,
        mission_id: str,
        correlation_id: str,
        quality_rng: random.Random | None = None,
    ) -> tuple[list[TelemetryFrame], QualityFlag, bool]:
        q_rng = quality_rng or rng
        elapsed_s = self.elapsed_for_tick(tick)
        timestamp = self.replay_epoch + timedelta(seconds=elapsed_s)
        raw_sensors = self.generate_sensors(tick, rng)
        sensor_quality = None
        if "sensorQuality" not in raw_sensors:
            sensor_quality = {
                key: SensorQuality(status=SensorQualityCode.OK)
                for key in ("chtCylindersC", "egtCylindersC")
                if key in raw_sensors
            }
            if sensor_quality:
                raw_sensors["sensorQuality"] = sensor_quality
        sensors = Sensors.model_validate(raw_sensors)
        rates = self.quality if elapsed_s >= self.inject_after_s else QualityRates()
        decision = decide_quality_event(q_rng, rates)
        base = TelemetryFrame(
            schemaVersion=self.schema_version,
            engineId=self.engine_id,
            missionId=mission_id,
            frameId=f"frame-{tick:06d}",
            correlationId=correlation_id,
            timestamp=timestamp,
            ingestTimestamp=timestamp,
            producerVersion=self.producer_version,
            sensors=sensors,
            qualityFlag=QualityFlag.OK,
            scenarioId=self.scenario_id,
        )
        frames = apply_quality_decision(base, decision)
        return frames, decision.flag, decision.skip_publish

    def replay(self, seed: int, mission_id: str, correlation_id: str) -> list[TelemetryFrame]:
        rng = rng_from_seed(seed)
        quality_rng = rng_from_seed(seed + 7919)
        published: list[TelemetryFrame] = []
        for tick in range(self.tick_count()):
            frames, _flag, skip_publish = self.build_frame(
                tick,
                rng,
                mission_id=mission_id,
                correlation_id=correlation_id,
                quality_rng=quality_rng,
            )
            if skip_publish:
                continue
            published.extend(frames)
        return published

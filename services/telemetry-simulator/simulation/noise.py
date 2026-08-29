from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import random

from app.contracts import QualityFlag, TelemetryFrame
from app.settings import QualityRates


SENSOR_BOUNDS: dict[str, tuple[float, float]] = {
    "rpm": (0.0, 4000.0),
    "oilPressureKpa": (0.0, 1000.0),
    "oilTempC": (-40.0, 200.0),
    "coolantTempC": (-40.0, 200.0),
    "vibrationMmS": (0.0, 50.0),
    "fuelFlowLph": (0.0, 100.0),
    "throttlePct": (0.0, 100.0),
    "altitudeM": (0.0, 12000.0),
    "ambientTempC": (-60.0, 60.0),
    "ambientPressureKpa": (10.0, 110.0),
    "alternatorVoltageV": (0.0, 40.0),
    "alternatorCurrentA": (-50.0, 150.0),
    "batteryVoltageV": (0.0, 40.0),
    "injectionTimingDeg": (-60.0, 60.0),
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def apply_jitter(value: float, jitter: float, rng: random.Random) -> float:
    if jitter <= 0:
        return value
    return value + rng.uniform(-jitter, jitter)


def clamp_sensor_value(name: str, value: float) -> float:
    bounds = SENSOR_BOUNDS.get(name)
    if bounds is None:
        return value
    return clamp(value, bounds[0], bounds[1])


def clamp_sensor_map(sensors: dict[str, object], rng: random.Random | None = None) -> dict[str, object]:
    clamped: dict[str, object] = {}
    for name, value in sensors.items():
        if name in {"chtCylindersC", "egtCylindersC"} and isinstance(value, list):
            jittered = []
            for item in value:
                number = float(item)
                if rng is not None:
                    number = apply_jitter(number, 0.0, rng)
                jittered.append(clamp(number, -40.0, 200.0) if name == "chtCylindersC" else clamp(number, 0.0, 1200.0))
            clamped[name] = jittered
        elif isinstance(value, (int, float)) and name in SENSOR_BOUNDS:
            clamped[name] = clamp_sensor_value(name, float(value))
        else:
            clamped[name] = value
    return clamped


class QualityDecision:
    def __init__(self, flag: QualityFlag, skip_publish: bool = False, duplicate: bool = False, shift_ms: int = 0):
        self.flag = flag
        self.skip_publish = skip_publish
        self.duplicate = duplicate
        self.shift_ms = shift_ms


def decide_quality_event(rng: random.Random, rates: QualityRates) -> QualityDecision:
    """Pick at most one quality event for a tick using the shared RNG."""
    roll = rng.random()
    cursor = 0.0
    cursor += rates.dropoutRate
    if roll < cursor:
        return QualityDecision(QualityFlag.DROPOUT, skip_publish=True)
    cursor += rates.dropoutFlagRate
    if roll < cursor:
        return QualityDecision(QualityFlag.DROPOUT)
    cursor += rates.duplicateRate
    if roll < cursor:
        return QualityDecision(QualityFlag.DUPLICATE, duplicate=True)
    cursor += rates.outOfOrderRate
    if roll < cursor:
        return QualityDecision(QualityFlag.OUT_OF_ORDER, shift_ms=rates.outOfOrderShiftMs)
    cursor += rates.degradedRate
    if roll < cursor:
        return QualityDecision(QualityFlag.DEGRADED)
    return QualityDecision(QualityFlag.OK)


def apply_quality_decision(frame: TelemetryFrame, decision: QualityDecision) -> list[TelemetryFrame]:
    """Return zero or more frames for this tick, each with the correct qualityFlag."""
    if decision.skip_publish:
        dropped = frame.model_copy(deep=True)
        dropped.qualityFlag = QualityFlag.DROPOUT
        return [dropped]

    primary = frame.model_copy(deep=True)
    if decision.flag == QualityFlag.OUT_OF_ORDER:
        primary.timestamp = primary.timestamp - timedelta(milliseconds=decision.shift_ms)
        if primary.ingestTimestamp is not None:
            primary.ingestTimestamp = primary.ingestTimestamp
        primary.qualityFlag = QualityFlag.OUT_OF_ORDER
        return [primary]

    if decision.flag == QualityFlag.DEGRADED:
        primary.qualityFlag = QualityFlag.DEGRADED
        return [primary]

    if decision.duplicate:
        original = frame.model_copy(deep=True)
        original.qualityFlag = QualityFlag.OK
        duplicate = deepcopy(original)
        duplicate.qualityFlag = QualityFlag.DUPLICATE
        return [original, duplicate]

    primary.qualityFlag = QualityFlag.OK
    return [primary]

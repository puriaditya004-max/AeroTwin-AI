"""Sensor deviation calculation and feature normalization.

Pure-Python, dependency-free. Shared by M2 (subsystem states) and M4 (fault fusion).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional

# Plausible range limits per sensor to detect dropped / disconnected / NaN signals
VALID_RANGES: Dict[str, tuple[float, float]] = {
    "rpm": (0.0, 4500.0),
    "oil_temp_c": (-40.0, 180.0),
    "coolant_temp_c": (-40.0, 160.0),
    "oil_pressure_psi": (0.0, 150.0),
    "oil_pressure_kpa": (0.0, 1000.0),
    "vibration_g": (0.0, 25.0),
    "vibration_mm_s": (0.0, 50.0),
    "fuel_flow_lph": (0.0, 120.0),
    "throttle_pct": (0.0, 100.0),
    "injection_timing_deg": (-60.0, 60.0),
}


def _sensor_key(sensor: str) -> str:
    head, _, tail = sensor.rpartition("_")
    if head and tail.isdigit():
        return head
    return sensor


def is_valid_reading(sensor: str, value: Optional[float]) -> bool:
    """Return True if reading is non-None, finite, and within physical sanity bounds."""
    if value is None:
        return False
    try:
        val = float(value)
    except (ValueError, TypeError):
        return False
    import math
    if math.isnan(val) or math.isinf(val):
        return False
    key = _sensor_key(sensor)
    if key in ("cht_cyl", "cht_cylinders_c"):
        return -40.0 <= val <= 350.0
    if key in ("egt_cyl", "egt_cylinders_c"):
        return -40.0 <= val <= 1100.0
    bounds = VALID_RANGES.get(key)
    if bounds is not None:
        return bounds[0] <= val <= bounds[1]
    return True


@dataclass(frozen=True)
class Deviation:
    sensor: str
    actual: float
    expected: float
    residual: float
    sigma: float
    z: float


def normalized_deviation(sensor: str, actual: float, expected: float, sigma: float) -> Deviation:
    """Calculate normalized deviation (z-score) between actual and context-expected value."""
    actual_f = float(actual)
    expected_f = float(expected)
    sigma_f = max(float(sigma), 1e-6)
    residual = actual_f - expected_f
    z = residual / sigma_f
    return Deviation(
        sensor=sensor,
        actual=round(actual_f, 3),
        expected=round(expected_f, 3),
        residual=round(residual, 3),
        sigma=round(sigma_f, 4),
        z=round(z, 3),
    )


def deviation_report(
    valid_readings: Mapping[str, float],
    expected_baselines: Mapping[str, float],
    sigmas: Mapping[str, float],
) -> Dict[str, Deviation]:
    """Generate a dictionary of Deviation objects for all valid sensors."""
    report: Dict[str, Deviation] = {}
    for sensor, actual in valid_readings.items():
        if sensor in expected_baselines and sensor in sigmas:
            report[sensor] = normalized_deviation(
                sensor, actual, expected_baselines[sensor], sigmas[sensor]
            )
    return report


class FeatureScaler:
    """Simple min-max or z-score feature scaler."""

    def __init__(self, means: Optional[Mapping[str, float]] = None, stds: Optional[Mapping[str, float]] = None):
        self.means = dict(means or {})
        self.stds = dict(stds or {})

    def scale(self, features: Mapping[str, float]) -> Dict[str, float]:
        scaled: Dict[str, float] = {}
        for k, v in features.items():
            mean = self.means.get(k, 0.0)
            std = self.stds.get(k, 1.0)
            scaled[k] = (float(v) - mean) / max(std, 1e-6)
        return scaled


__all__ = [
    "Deviation",
    "FeatureScaler",
    "is_valid_reading",
    "normalized_deviation",
    "deviation_report",
]

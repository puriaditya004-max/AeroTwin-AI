"""Ambient temperature model for engine thermal dissipation and tolerance scaling.

Pure-Python, dependency-free. Shared by M2 (subsystem states) and M4 (fault fusion).
All temperatures are in deg C.
"""
from __future__ import annotations

from typing import Optional

EXTREME_COLD_THRESHOLD_C = -10.0
EXTREME_HOT_THRESHOLD_C = 35.0
NOMINAL_AMBIENT_C = 15.0

THERMAL_SENSOR_PREFIXES = ("oil_temp", "coolant_temp", "cht_cyl", "egt_cyl")


def is_thermal_sensor(sensor: str) -> bool:
    """Return True if sensor is part of the thermal subsystem."""
    return any(sensor.startswith(prefix) for prefix in THERMAL_SENSOR_PREFIXES)


def is_extreme_ambient(oat_c: float) -> bool:
    """Return True if outside nominal ambient thermal operating envelope."""
    return oat_c < EXTREME_COLD_THRESHOLD_C or oat_c > EXTREME_HOT_THRESHOLD_C


def thermal_tolerance_scale(oat_c: float) -> float:
    """Widens thermal sigma/tolerances on hot or cold days to prevent false alarms.

    Returns a scale factor (>= 1.0) applied to thermal sensor standard deviations.
    """
    if oat_c > EXTREME_HOT_THRESHOLD_C:
        delta = oat_c - EXTREME_HOT_THRESHOLD_C
        return min(2.0, 1.0 + 0.05 * delta)
    if oat_c < EXTREME_COLD_THRESHOLD_C:
        delta = EXTREME_COLD_THRESHOLD_C - oat_c
        return min(1.8, 1.0 + 0.04 * delta)
    return 1.0


def compensate_thermal_baseline(
    sensor: str,
    base_temp_c: float,
    oat_c: float,
    thermal_coupling_factor: float = 0.35,
) -> float:
    """Context-adjusts thermal baseline according to ambient temperature offset from ISA (15 C)."""
    if not is_thermal_sensor(sensor):
        return float(base_temp_c)
    delta_ambient = float(oat_c) - NOMINAL_AMBIENT_C
    return float(base_temp_c) + thermal_coupling_factor * delta_ambient


__all__ = [
    "is_thermal_sensor",
    "is_extreme_ambient",
    "thermal_tolerance_scale",
    "compensate_thermal_baseline",
]

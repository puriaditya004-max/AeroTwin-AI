"""Operating point estimator and context-adjusted nominal baseline generator.

Pure-Python, dependency-free. Shared by M2 (subsystem states) and M4 (fault fusion).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Mapping, Optional

from .altitude_model import compensate_baseline
from .ambient_model import compensate_thermal_baseline

N_CYLINDERS = 4


class FlightPhase(str, Enum):
    IDLE = "IDLE"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    DESCENT = "DESCENT"


# Nominal standard deviation (1-sigma) expected under steady cruise
SENSOR_SIGMA: Dict[str, float] = {
    "rpm": 30.0,
    "oil_temp_c": 3.0,
    "coolant_temp_c": 3.0,
    "oil_pressure_psi": 4.0,
    "oil_pressure_kpa": 27.5,
    "vibration_g": 0.35,
    "vibration_mm_s": 0.8,
    "fuel_flow_lph": 2.0,
    "throttle_pct": 2.0,
    "injection_timing_deg": 0.8,
}
for i in range(1, N_CYLINDERS + 1):
    SENSOR_SIGMA[f"cht_cyl_{i}"] = 6.0
    SENSOR_SIGMA[f"egt_cyl_{i}"] = 18.0


@dataclass
class OperatingPoint:
    rpm: float
    throttle_pct: float
    engine_load_pct: float
    phase: FlightPhase
    transient: bool = False
    throttle_rate_pct_s: float = 0.0


def sensor_sigma(sensor: str) -> float:
    """Return nominal standard deviation for a sensor."""
    return SENSOR_SIGMA.get(sensor, 2.5)


def transient_sigma_scale(sensor: str) -> float:
    """Scale factor applied to sensor sigma during transient conditions."""
    if sensor in ("rpm", "throttle_pct", "fuel_flow_lph", "vibration_g", "vibration_mm_s"):
        return 2.5
    return 1.6


def build_operating_point(
    readings: Mapping[str, Optional[float]],
    context: Optional[Mapping[str, float]] = None,
) -> OperatingPoint:
    """Infer the current operating point and flight phase."""
    ctx = dict(context or {})
    rpm = float(readings.get("rpm") or ctx.get("rpm") or 2400.0)
    throttle = float(readings.get("throttle_pct") or ctx.get("throttle_pct") or 65.0)
    load = float(readings.get("engine_load_pct") or ctx.get("engine_load_pct") or (0.6 * throttle + 0.4 * (rpm / 2800.0) * 100.0))
    climb_rate = float(ctx.get("climb_rate_fpm") or 0.0)
    throttle_rate = float(ctx.get("throttle_rate_pct_s") or 0.0)
    transient = abs(throttle_rate) > 5.0 or bool(ctx.get("transient", False))

    if throttle < 20.0 and rpm < 1200.0:
        phase = FlightPhase.IDLE
    elif throttle > 90.0 and climb_rate > 300.0:
        phase = FlightPhase.TAKEOFF
    elif climb_rate > 300.0:
        phase = FlightPhase.CLIMB
    elif climb_rate < -300.0:
        phase = FlightPhase.DESCENT
    else:
        phase = FlightPhase.CRUISE

    return OperatingPoint(
        rpm=rpm,
        throttle_pct=throttle,
        engine_load_pct=round(load, 2),
        phase=phase,
        transient=transient,
        throttle_rate_pct_s=round(throttle_rate, 2),
    )


def expected_baselines(
    op: OperatingPoint,
    altitude_ft: float = 0.0,
    oat_c: float = 15.0,
) -> Dict[str, float]:
    """Generate expected context-adjusted nominal baselines for all sensors."""
    load = op.engine_load_pct
    base_oil_temp = 75.0 + 0.35 * load
    base_coolant_temp = 72.0 + 0.30 * load
    base_oil_press_psi = 45.0 + 0.35 * load
    base_oil_press_kpa = 310.0 + 2.4 * load
    base_vib_g = 1.0 + 0.03 * load
    base_vib_mm_s = 1.0 + 0.035 * load
    base_fuel_flow = 10.0 + 0.45 * load

    baselines: Dict[str, float] = {
        "rpm": float(op.rpm),
        "throttle_pct": float(op.throttle_pct),
        "engine_load_pct": float(load),
        "fuel_flow_lph": round(base_fuel_flow, 2),
        "oil_temp_c": round(compensate_thermal_baseline("oil_temp_c", base_oil_temp, oat_c), 2),
        "coolant_temp_c": round(compensate_thermal_baseline("coolant_temp_c", base_coolant_temp, oat_c), 2),
        "oil_pressure_psi": round(compensate_baseline("oil_pressure_psi", base_oil_press_psi, altitude_ft, oat_c), 2),
        "oil_pressure_kpa": round(compensate_baseline("oil_pressure_kpa", base_oil_press_kpa, altitude_ft, oat_c), 2),
        "vibration_g": round(base_vib_g, 3),
        "vibration_mm_s": round(base_vib_mm_s, 3),
        "injection_timing_deg": 12.0,
    }

    for i in range(1, N_CYLINDERS + 1):
        cht_base = 135.0 + 0.60 * load
        egt_base = 650.0 + 1.20 * load
        cht_comp = compensate_thermal_baseline(f"cht_cyl_{i}", cht_base, oat_c)
        egt_comp = compensate_baseline(f"egt_cyl_{i}", egt_base, altitude_ft, oat_c)
        baselines[f"cht_cyl_{i}"] = round(cht_comp, 2)
        baselines[f"egt_cyl_{i}"] = round(egt_comp, 2)

    return baselines


__all__ = [
    "N_CYLINDERS",
    "FlightPhase",
    "OperatingPoint",
    "SENSOR_SIGMA",
    "sensor_sigma",
    "transient_sigma_scale",
    "build_operating_point",
    "expected_baselines",
]

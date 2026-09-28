"""Operating-point model: context-aware expected sensor baselines.

Expected values depend on throttle (-> load), flight phase (cruise/climb/descent/takeoff),
altitude and ambient temperature. Thermal sensors follow load; phase adds cooling-airflow offsets.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Mapping, Optional

from . import altitude_model as alt
from . import ambient_model as amb
from .altitude_model import sensor_family

N_CYLINDERS = 4
CRUISE_LOAD_PCT = 70.0


class FlightPhase(str, Enum):
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    DESCENT = "DESCENT"


# Sea-level ISA cruise baselines (70 % load).
CRUISE_BASELINES: Dict[str, float] = {
    "oil_temp_c": 90.0,
    "oil_pressure_psi": 60.0,
    "coolant_temp_c": 85.0,
    "vibration_g": 0.80,
    "fuel_flow_lph": 22.0,
    "injection_timing_deg": 12.0,
}
for _i in range(1, N_CYLINDERS + 1):
    CRUISE_BASELINES[f"cht_cyl_{_i}"] = 190.0
    CRUISE_BASELINES[f"egt_cyl_{_i}"] = 650.0

# Baseline change per +1 % load relative to cruise.
LOAD_SENSITIVITY: Dict[str, float] = {
    "oil_temp_c": 0.25, "oil_pressure_psi": -0.03, "coolant_temp_c": 0.15, "vibration_g": 0.004,
    "fuel_flow_lph": 0.31, "cht_cyl": 0.70, "egt_cyl": 2.0,
}

# Cooling-airflow / power-setting offsets by phase.
PHASE_OFFSETS: Dict[FlightPhase, Dict[str, float]] = {
    FlightPhase.CRUISE: {},
    FlightPhase.CLIMB: {"cht_cyl": 10.0, "oil_temp_c": 2.0, "coolant_temp_c": 2.0},
    FlightPhase.TAKEOFF: {"cht_cyl": 15.0, "oil_temp_c": 3.0, "coolant_temp_c": 3.0},
    FlightPhase.DESCENT: {"cht_cyl": -8.0},
}

# 1-sigma normal scatter of (actual - expected) at the given operating point.
SENSOR_SIGMA: Dict[str, float] = {
    "oil_temp_c": 4.0, "oil_pressure_psi": 4.0, "coolant_temp_c": 3.0, "cht_cyl": 8.0, "egt_cyl": 25.0,
    "vibration_g": 0.15, "fuel_flow_lph": 2.0, "injection_timing_deg": 0.5, "rpm": 60.0,
    "engine_load_pct": 6.0, "manifold_pressure_inhg": 1.0,
}

# Tolerance widening while a throttle transient is settling (thermal lag, overshoot).
TRANSIENT_SIGMA_SCALE: Dict[str, float] = {
    "oil_temp_c": 2.0, "coolant_temp_c": 2.0, "cht_cyl": 2.0, "egt_cyl": 2.5, "vibration_g": 2.0,
    "oil_pressure_psi": 1.5, "fuel_flow_lph": 2.5, "rpm": 2.5, "engine_load_pct": 2.5,
    "manifold_pressure_inhg": 2.5,
}

TRANSIENT_RATE_PCT_S = 8.0
TRANSIENT_STEP_PCT = 20.0
TRANSIENT_WINDOW_S = 45.0


def sensor_sigma(sensor: str) -> float:
    return SENSOR_SIGMA.get(sensor_family(sensor), 1.0)


def transient_sigma_scale(sensor: str) -> float:
    return TRANSIENT_SIGMA_SCALE.get(sensor_family(sensor), 1.0)


@dataclass(frozen=True)
class OperatingPoint:
    phase: FlightPhase
    throttle_pct: float
    vertical_speed_fpm: float = 0.0
    throttle_rate_pct_s: float = 0.0
    transient: bool = False


def classify_phase(vertical_speed_fpm: float, throttle_pct: float, altitude_agl_ft: Optional[float] = None) -> FlightPhase:
    if vertical_speed_fpm >= 300 and throttle_pct >= 95 and altitude_agl_ft is not None and altitude_agl_ft < 1000:
        return FlightPhase.TAKEOFF
    if vertical_speed_fpm >= 300:
        return FlightPhase.CLIMB
    if vertical_speed_fpm <= -300:
        return FlightPhase.DESCENT
    return FlightPhase.CRUISE


def detect_transient(
    throttle_rate_pct_s: float = 0.0,
    seconds_since_throttle_step: Optional[float] = None,
    throttle_step_pct: float = 0.0,
) -> bool:
    """Transient while throttle is moving fast, or shortly after a large throttle step."""
    if abs(throttle_rate_pct_s) >= TRANSIENT_RATE_PCT_S:
        return True
    return (
        seconds_since_throttle_step is not None
        and seconds_since_throttle_step <= TRANSIENT_WINDOW_S
        and abs(throttle_step_pct) >= TRANSIENT_STEP_PCT
    )


def build_operating_point(readings: Mapping[str, float], context: Optional[Mapping[str, float]] = None) -> OperatingPoint:
    ctx = context or {}
    thr = readings.get("throttle_pct")
    thr = 65.0 if thr is None else float(thr)
    vs = float(ctx.get("vertical_speed_fpm", 0.0))
    rate = float(ctx.get("throttle_rate_pct_s", 0.0))
    return OperatingPoint(
        phase=classify_phase(vs, thr, ctx.get("altitude_agl_ft")),
        throttle_pct=thr,
        vertical_speed_fpm=vs,
        throttle_rate_pct_s=rate,
        transient=detect_transient(rate, ctx.get("seconds_since_throttle_step"), float(ctx.get("throttle_step_pct", 0.0))),
    )


def expected_load_pct(throttle_pct: float, pressure_altitude_ft: float, oat_c: Optional[float]) -> float:
    return min(110.0, alt.compensate_baseline("engine_load_pct", 1.08 * throttle_pct, pressure_altitude_ft, oat_c))


def expected_baselines(op: OperatingPoint, pressure_altitude_ft: float = 0.0, oat_c: Optional[float] = None) -> Dict[str, float]:
    """Expected value of every diagnostic sensor at this operating point and environment."""
    if oat_c is None:
        oat_c = alt.isa_temperature_c(pressure_altitude_ft)
    load = expected_load_pct(op.throttle_pct, pressure_altitude_ft, oat_c)
    d_load = load - CRUISE_LOAD_PCT
    out: Dict[str, float] = {
        "rpm": 1000.0 + 21.5 * op.throttle_pct,
        "engine_load_pct": load,
        "manifold_pressure_inhg": alt.compensate_baseline(
            "manifold_pressure_inhg", 29.92 * (0.35 + 0.65 * op.throttle_pct / 100.0), pressure_altitude_ft, oat_c
        ),
    }
    offsets = PHASE_OFFSETS[op.phase]
    for name, base in CRUISE_BASELINES.items():
        fam = sensor_family(name)
        v = base + LOAD_SENSITIVITY.get(fam, 0.0) * d_load + offsets.get(fam, 0.0)
        v = alt.compensate_baseline(name, v, pressure_altitude_ft, oat_c)
        if amb.is_thermal_sensor(name):
            v = amb.compensate_thermal_baseline(name, v, oat_c, load / CRUISE_LOAD_PCT)
        out[name] = v
    return out


__all__ = [
    "FlightPhase", "OperatingPoint", "CRUISE_BASELINES", "SENSOR_SIGMA", "N_CYLINDERS", "sensor_sigma",
    "transient_sigma_scale", "classify_phase", "detect_transient", "build_operating_point",
    "expected_load_pct", "expected_baselines",
]

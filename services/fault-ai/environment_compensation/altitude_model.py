"""Altitude model: ISA atmosphere, density altitude and altitude-compensated baselines.

Pure-Python, dependency-free. Shared by M2 (subsystem states) and M4 (fault fusion).
All altitudes are in feet, temperatures in deg C, pressures in hPa.
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional

ISA_SEA_LEVEL_TEMP_C = 15.0
ISA_SEA_LEVEL_PRESSURE_HPA = 1013.25
ISA_LAPSE_C_PER_FT = 0.0019812  # 1.9812 C per 1000 ft (troposphere)
_TROPOPAUSE_FT = 36089.0
_MIN_ALT_FT = -2000.0
_PRESSURE_COEF = 6.8756e-6
_PRESSURE_EXP = 5.2559


def sensor_family(sensor: str) -> str:
    """'cht_cyl_3' -> 'cht_cyl'; 'oil_temp_c' -> 'oil_temp_c'."""
    head, _, tail = sensor.rpartition("_")
    return head if head and tail.isdigit() else sensor


def _clamp_alt(altitude_ft: float) -> float:
    return max(_MIN_ALT_FT, min(float(altitude_ft), _TROPOPAUSE_FT))


def isa_temperature_c(pressure_altitude_ft: float) -> float:
    """ISA standard temperature at a pressure altitude."""
    return ISA_SEA_LEVEL_TEMP_C - ISA_LAPSE_C_PER_FT * _clamp_alt(pressure_altitude_ft)


def isa_pressure_hpa(pressure_altitude_ft: float) -> float:
    """ISA static pressure at a pressure altitude."""
    h = _clamp_alt(pressure_altitude_ft)
    return ISA_SEA_LEVEL_PRESSURE_HPA * (1.0 - _PRESSURE_COEF * h) ** _PRESSURE_EXP


def pressure_ratio(pressure_altitude_ft: float) -> float:
    """delta = P / P0."""
    return isa_pressure_hpa(pressure_altitude_ft) / ISA_SEA_LEVEL_PRESSURE_HPA


def pressure_lapse_rate_hpa_per_kft(pressure_altitude_ft: float) -> float:
    """Local pressure change per +1000 ft (negative number)."""
    return isa_pressure_hpa(pressure_altitude_ft + 500.0) - isa_pressure_hpa(pressure_altitude_ft - 500.0)


def pressure_altitude_ft(indicated_altitude_ft: float, qnh_hpa: float = ISA_SEA_LEVEL_PRESSURE_HPA) -> float:
    """Pressure altitude from indicated altitude and altimeter setting (QNH)."""
    return indicated_altitude_ft + 145366.45 * (1.0 - (qnh_hpa / ISA_SEA_LEVEL_PRESSURE_HPA) ** 0.190284)


def density_altitude_ft(pressure_altitude_ft_: float, oat_c: float) -> float:
    """Density altitude = PA + 118.8 * (OAT - ISA temp)."""
    return pressure_altitude_ft_ + 118.8 * (oat_c - isa_temperature_c(pressure_altitude_ft_))


def density_ratio(pressure_altitude_ft_: float, oat_c: Optional[float] = None) -> float:
    """sigma = rho / rho0 for the given pressure altitude and OAT (ISA temp if OAT is None)."""
    if oat_c is None:
        oat_c = isa_temperature_c(pressure_altitude_ft_)
    return pressure_ratio(pressure_altitude_ft_) * (273.15 + ISA_SEA_LEVEL_TEMP_C) / (273.15 + oat_c)


# sensor family -> compensation rule
#   ("scale", "pressure"|"density")  : multiply sea-level baseline by delta or sigma
#   ("offset_per_kft", x)            : add x per 1000 ft of density altitude (lean-out heuristic)
_RULES: Dict[str, tuple] = {
    "engine_load_pct": ("scale", "density"),
    "manifold_pressure_inhg": ("scale", "pressure"),
    "egt_cyl": ("offset_per_kft", 2.8),
}


def compensate_baseline(
    sensor: str,
    sea_level_value: float,
    pressure_altitude_ft_: float,
    oat_c: Optional[float] = None,
) -> float:
    """Return the altitude-compensated expected value for one sensor."""
    rule = _RULES.get(sensor_family(sensor))
    if rule is None:
        return float(sea_level_value)
    kind, arg = rule
    if kind == "scale":
        factor = (
            density_ratio(pressure_altitude_ft_, oat_c)
            if arg == "density"
            else pressure_ratio(pressure_altitude_ft_)
        )
        return float(sea_level_value) * factor
    if kind == "offset_per_kft":
        da = density_altitude_ft(
            pressure_altitude_ft_, isa_temperature_c(pressure_altitude_ft_) if oat_c is None else oat_c
        )
        return float(sea_level_value) + arg * max(da, 0.0) / 1000.0
    return float(sea_level_value)


def altitude_compensated_baselines(
    baselines: Mapping[str, float],
    pressure_altitude_ft_: float,
    oat_c: Optional[float] = None,
) -> Dict[str, float]:
    """Compensate a whole dict of sea-level baselines."""
    return {k: compensate_baseline(k, v, pressure_altitude_ft_, oat_c) for k, v in baselines.items()}


__all__ = [
    "sensor_family", "isa_temperature_c", "isa_pressure_hpa", "pressure_ratio",
    "pressure_lapse_rate_hpa_per_kft", "pressure_altitude_ft", "density_altitude_ft",
    "density_ratio", "compensate_baseline", "altitude_compensated_baselines",
]

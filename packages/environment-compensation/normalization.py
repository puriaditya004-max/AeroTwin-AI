"""Standardized feature scaling and actual-minus-expected deviation normalization."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

from .altitude_model import sensor_family

PHYSICAL_LIMITS: Dict[str, tuple] = {
    "rpm": (0.0, 3600.0),
    "throttle_pct": (0.0, 100.0),
    "engine_load_pct": (0.0, 130.0),
    "oil_temp_c": (-40.0, 200.0),
    "oil_pressure_psi": (0.0, 150.0),
    "coolant_temp_c": (-40.0, 160.0),
    "cht_cyl": (-40.0, 450.0),
    "egt_cyl": (0.0, 1200.0),
    "vibration_g": (0.0, 25.0),
    "fuel_flow_lph": (0.0, 100.0),
    "injection_timing_deg": (-15.0, 45.0),
    "manifold_pressure_inhg": (0.0, 45.0),
}
# A reading of exactly 0.0 from these sensors in flight is a dropout signature.
ZERO_IS_DROPOUT = {"oil_temp_c", "coolant_temp_c", "cht_cyl", "egt_cyl"}


def is_valid_reading(sensor: str, value) -> bool:
    """False for None/NaN/inf/out-of-range/zero-dropout values."""
    if value is None or isinstance(value, bool):
        return False
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(v):
        return False
    fam = sensor_family(sensor)
    lo, hi = PHYSICAL_LIMITS.get(fam, (-math.inf, math.inf))
    if not lo <= v <= hi:
        return False
    if fam in ZERO_IS_DROPOUT and v == 0.0:
        return False
    return True


def deviation(actual: float, expected: float) -> float:
    """Raw actual-minus-expected."""
    return float(actual) - float(expected)


def normalized_deviation(actual: float, expected: float, sigma: float) -> float:
    """(actual - expected) / sigma, i.e. a z-like score."""
    return (float(actual) - float(expected)) / max(float(sigma), 1e-9)


@dataclass(frozen=True)
class Deviation:
    sensor: str
    actual: float
    expected: float
    deviation: float
    z: float


def deviation_report(
    actual: Mapping[str, float],
    expected: Mapping[str, float],
    sigma: Mapping[str, float],
) -> Dict[str, Deviation]:
    """Deviation of every sensor present in both `actual` and `expected`."""
    out: Dict[str, Deviation] = {}
    for sensor, value in actual.items():
        if sensor not in expected or sensor not in sigma:
            continue
        d = deviation(value, expected[sensor])
        out[sensor] = Deviation(sensor, float(value), float(expected[sensor]), d, d / max(sigma[sensor], 1e-9))
    return out


def zscore(x: float, mean: float, std: float) -> float:
    return (x - mean) / max(std, 1e-9)


def minmax_scale(x: float, lo: float, hi: float) -> float:
    """Scale to [0, 1], clipped."""
    if hi <= lo:
        return 0.0
    return min(1.0, max(0.0, (x - lo) / (hi - lo)))


def robust_scale(values: Sequence[float]) -> tuple:
    """Return (median, 1.4826*MAD) for outlier-resistant scaling."""
    vals = sorted(float(v) for v in values)
    if not vals:
        return 0.0, 1.0
    n = len(vals)
    med = vals[n // 2] if n % 2 else 0.5 * (vals[n // 2 - 1] + vals[n // 2])
    dev = sorted(abs(v - med) for v in vals)
    mad = dev[n // 2] if n % 2 else 0.5 * (dev[n // 2 - 1] + dev[n // 2])
    return med, max(1.4826 * mad, 1e-9)


class FeatureScaler:
    """Per-feature standard scaler (fit on nominal data, transform new rows)."""

    def __init__(self) -> None:
        self.mean: Dict[str, float] = {}
        self.std: Dict[str, float] = {}

    def fit(self, rows: Iterable[Mapping[str, float]]) -> "FeatureScaler":
        cols: Dict[str, List[float]] = {}
        for row in rows:
            for k, v in row.items():
                if is_valid_reading(k, v):
                    cols.setdefault(k, []).append(float(v))
        for k, vals in cols.items():
            m = sum(vals) / len(vals)
            var = sum((v - m) ** 2 for v in vals) / max(len(vals) - 1, 1)
            self.mean[k], self.std[k] = m, max(math.sqrt(var), 1e-9)
        return self

    def transform(self, row: Mapping[str, float]) -> Dict[str, float]:
        return {k: zscore(float(v), self.mean[k], self.std[k]) for k, v in row.items() if k in self.mean and is_valid_reading(k, v)}

    def inverse(self, row: Mapping[str, float]) -> Dict[str, float]:
        return {k: v * self.std[k] + self.mean[k] for k, v in row.items() if k in self.mean}


__all__ = [
    "PHYSICAL_LIMITS", "is_valid_reading", "deviation", "normalized_deviation", "Deviation",
    "deviation_report", "zscore", "minmax_scale", "robust_scale", "FeatureScaler",
]

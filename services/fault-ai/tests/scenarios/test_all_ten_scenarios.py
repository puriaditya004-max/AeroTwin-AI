"""End-to-end scenario test suite covering all 10 mandatory evaluation scenarios.

Scenarios
---------
1. Normal cruise
2. High / low altitude
3. Hot / cold ambient temp
4. Climb / descent
5. Rapid throttle increase
6. Sensor dropout / drift
7. Oil pressure degradation
8. Overheating
9. Misfire / vibration
10. Multiple simultaneous faults
"""
from __future__ import annotations

import math
import random
from typing import Dict

import pytest

from models.fusion import (
    ENGINE_FAULTS,
    FaultFusionEngine,
    FusionResult,
    Severity,
    ec,
)

ENGINE = FaultFusionEngine()


def nominal(throttle: float = 65.0, pa_ft: float = 0.0, oat_c: float = 15.0) -> Dict[str, float]:
    op = ec.build_operating_point({"throttle_pct": throttle}, {"altitude_ft": pa_ft, "oat_c": oat_c})
    return ec.expected_baselines(op, pa_ft, oat_c)


def bump(readings: Dict[str, float], **kwargs: float) -> Dict[str, float]:
    out = dict(readings)
    for k, delta in kwargs.items():
        if k in out:
            out[k] += delta
        else:
            out[k] = delta
    return out


def cyl_bump(readings: Dict[str, float], prefix: str, delta: float) -> Dict[str, float]:
    out = dict(readings)
    for k in list(out):
        if k.startswith(prefix):
            out[k] += delta
    return out


def jitter(readings: Dict[str, float], rng: random.Random, scale: float = 0.5) -> Dict[str, float]:
    out = dict(readings)
    for k in list(out):
        sigma = ec.sensor_sigma(k)
        out[k] += rng.gauss(0.0, sigma * scale)
    return out


def types(res: FusionResult) -> set[str]:
    return {f.fault_type for f in res.findings} | {res.fault_type}


def has_line(res: FusionResult, text: str) -> bool:
    return any(text in e for e in res.evidence)


# ------------------------------------------------------------------ 1. Normal cruise
def test_s01_normal_cruise():
    rng = random.Random(42)
    base = nominal()
    for _ in range(100):
        r = jitter(base, rng, scale=0.6)
        res = ENGINE.diagnose(r)
        assert res.fault_type == "NORMAL", res.evidence
        assert res.severity < Severity.WARNING


# ------------------------------------------------------------------ 2. High / low altitude
def test_s02_high_altitude_baseline():
    rng = random.Random(101)
    base_high = nominal(pa_ft=10000.0, oat_c=-5.0)
    for _ in range(50):
        r = jitter(base_high, rng, scale=0.6)
        res = ENGINE.diagnose(r, {"altitude_ft": 10000.0, "oat_c": -5.0})
        assert res.fault_type == "NORMAL", res.evidence


def test_s02_low_altitude_baseline():
    rng = random.Random(102)
    base_low = nominal(pa_ft=500.0, oat_c=25.0)
    for _ in range(50):
        r = jitter(base_low, rng, scale=0.6)
        res = ENGINE.diagnose(r, {"altitude_ft": 500.0, "oat_c": 25.0})
        assert res.fault_type == "NORMAL", res.evidence


# ------------------------------------------------------------------ 3. Hot / cold ambient temp
def test_s03_hot_ambient_temp():
    rng = random.Random(201)
    base_hot = nominal(throttle=70.0, pa_ft=2000.0, oat_c=42.0)
    for _ in range(50):
        r = jitter(base_hot, rng, scale=0.6)
        res = ENGINE.diagnose(r, {"altitude_ft": 2000.0, "oat_c": 42.0})
        assert res.fault_type == "NORMAL", res.evidence


def test_s03_cold_ambient_temp():
    rng = random.Random(202)
    base_cold = nominal(throttle=70.0, pa_ft=5000.0, oat_c=-15.0)
    for _ in range(50):
        r = jitter(base_cold, rng, scale=0.6)
        res = ENGINE.diagnose(r, {"altitude_ft": 5000.0, "oat_c": -15.0})
        assert res.fault_type == "NORMAL", res.evidence


# ------------------------------------------------------------------ 4. Climb / descent
def test_s04_descent_thermal_lag_is_transient_not_permanent_fault():
    # throttle chopped 65 -> 30 ; heads/oil still hot for a while
    lagged = cyl_bump(bump(nominal(throttle=30), oil_temp_c=9, coolant_temp_c=5), "cht_cyl", 30)
    ctx = {"vertical_speed_fpm": -800, "seconds_since_throttle_step": 10, "throttle_step_pct": -35}
    res = ENGINE.diagnose(lagged, ctx)
    assert res.operating_phase == "DESCENT" and res.transient
    assert res.fault_type == "NORMAL" and has_line(res, "Transient condition")
    # same readings long after the step are no longer excused
    ctx["seconds_since_throttle_step"] = 300
    assert ENGINE.diagnose(lagged, ctx).fault_type == "OVERHEATING"


def test_s04_steady_descent_not_flagged():
    rng = random.Random(44)
    r = cyl_bump(nominal(throttle=30), "cht_cyl", -8)
    for _ in range(100):
        assert ENGINE.diagnose(jitter(r, rng), {"vertical_speed_fpm": -700}).fault_type == "NORMAL"


# ------------------------------------------------------------------ 5. Rapid throttle increase
def test_s05_rapid_throttle_increase_handled_gracefully():
    lo, hi = nominal(throttle=50), nominal(throttle=95)
    r = {k: (lo[k] + 0.4 * (hi[k] - lo[k]) if ec.ambient_model.is_thermal_sensor(k) else hi[k]) for k in hi}
    r = cyl_bump(r, "egt_cyl", 60)  # EGT overshoot
    r["oil_pressure_psi"] -= 5.0     # brief pressure sag
    res = ENGINE.diagnose(r, {"throttle_rate_pct_s": 15.0})
    assert res.transient
    assert res.severity < Severity.WARNING and res.fault_type == "NORMAL"
    assert has_line(res, "Transient condition")


def test_s05_transient_never_reaches_critical():
    r = cyl_bump(bump(nominal(throttle=95), oil_temp_c=60, coolant_temp_c=45), "cht_cyl", 120)
    res = ENGINE.diagnose(r, {"throttle_rate_pct_s": 15.0})
    assert res.fault_type == "OVERHEATING" and res.severity == Severity.HIGH


# ------------------------------------------------------------------ 6. Sensor dropout / drift
@pytest.mark.parametrize("sensor,value", [
    ("oil_temp_c", None), ("coolant_temp_c", 0.0), ("cht_cyl_2", float("nan")), ("egt_cyl_3", -999.0),
])
def test_s06_dropout_yields_sensor_fault(sensor, value):
    r = nominal()
    r[sensor] = value
    res = ENGINE.diagnose(r)
    assert res.fault_type == "SENSOR_FAULT" and res.component == sensor
    assert not (types(res) & set(ENGINE_FAULTS))
    assert has_line(res, f"Partial diagnosis active — required sensor: {sensor} missing")


@pytest.mark.parametrize("sensor,delta", [("coolant_temp_c", 35.0), ("oil_temp_c", 40.0), ("cht_cyl_2", 70.0), ("oil_pressure_psi", -45.0)])
def test_s06_isolated_drift_yields_sensor_fault(sensor, delta):
    res = ENGINE.diagnose(bump(nominal(), **{sensor: delta}))
    assert res.fault_type == "SENSOR_FAULT" and res.component == sensor
    assert not (types(res) & set(ENGINE_FAULTS))


# ------------------------------------------------------------------ 7. Oil pressure degradation
def test_s07_oil_pressure_degradation_critical():
    res = ENGINE.diagnose(bump(nominal(), oil_pressure_psi=-35, oil_temp_c=15))
    assert res.fault_type == "OIL_PRESSURE_DEGRADATION" and res.severity == Severity.CRITICAL
    assert res.component == "oil_pump" and has_line(res, "oil_pressure_psi")


def test_s07_oil_pressure_mild_is_high_not_critical():
    res = ENGINE.diagnose(bump(nominal(), oil_pressure_psi=-16, oil_temp_c=14))
    assert res.fault_type == "OIL_PRESSURE_DEGRADATION" and res.severity == Severity.HIGH


# ------------------------------------------------------------------ 8. Overheating
def test_s08_overheating_critical_with_evidence():
    res = ENGINE.diagnose(cyl_bump(bump(nominal(), oil_temp_c=25, coolant_temp_c=20), "cht_cyl", 50))
    assert res.fault_type == "OVERHEATING" and res.severity == Severity.CRITICAL
    assert len([e for e in res.evidence if "expected" in e]) >= 3
    assert has_line(res, "Multi-sensor evidence")


def test_s08_overheating_moderate_is_high():
    res = ENGINE.diagnose(cyl_bump(bump(nominal(), oil_temp_c=14, coolant_temp_c=11), "cht_cyl", 26))
    assert res.fault_type == "OVERHEATING" and res.severity == Severity.HIGH


def test_s08_single_cylinder_localization():
    res = ENGINE.diagnose(bump(nominal(), cht_cyl_3=70, oil_temp_c=14))
    assert res.fault_type == "OVERHEATING" and res.component == "cylinder_3_head"


# ------------------------------------------------------------------ 9. Misfire / vibration
def test_s09_misfire_vibration():
    res = ENGINE.diagnose(bump(nominal(), vibration_g=0.9, egt_cyl_2=-180))
    assert res.fault_type == "VIBRATION_MISFIRE" and res.component == "cylinder_2"
    assert res.severity == Severity.CRITICAL


def test_s09_injection_timing_fault():
    res = ENGINE.diagnose(bump(nominal(), vibration_g=0.7, injection_timing_deg=3.0))
    assert res.fault_type == "VIBRATION_MISFIRE" and res.component == "injection_system"


# ------------------------------------------------------------------ 10. Multiple simultaneous faults
def test_s10_oil_pressure_plus_thermal_runaway_both_reported():
    r = cyl_bump(bump(nominal(), oil_pressure_psi=-35, oil_temp_c=30, coolant_temp_c=20), "cht_cyl", 50)
    res = ENGINE.diagnose(r)
    assert {"OIL_PRESSURE_DEGRADATION", "OVERHEATING"} <= types(res)
    assert all(f.severity == Severity.CRITICAL for f in res.findings if f.fault_type in ENGINE_FAULTS)
    assert res.fault_type in ("OIL_PRESSURE_DEGRADATION", "OVERHEATING")
    assert any(a["fault_type"] in ("OIL_PRESSURE_DEGRADATION", "OVERHEATING") for a in res.alternatives)
    assert has_line(res, "[OVERHEATING]") and has_line(res, "[OIL_PRESSURE_DEGRADATION]")
    assert has_line(res, "Concurrent finding retained")


def test_s10_misfire_plus_oil_pressure_not_merged():
    res = ENGINE.diagnose(bump(nominal(), vibration_g=0.9, egt_cyl_2=-180, oil_pressure_psi=-30, oil_temp_c=14))
    assert {"VIBRATION_MISFIRE", "OIL_PRESSURE_DEGRADATION"} <= types(res)
    assert "OVERHEATING" not in types(res)
    comp = {f.fault_type: f.component for f in res.findings}
    assert comp["VIBRATION_MISFIRE"] == "cylinder_2" and comp["OIL_PRESSURE_DEGRADATION"] == "oil_pump"


# ------------------------------------------------------------------ Safeguards (Task 3)
def test_safeguard_single_sensor_never_critical():
    res = ENGINE.diagnose({"throttle_pct": 65.0, "oil_temp_c": 130.0})
    assert res.fault_type == "OVERHEATING" and res.severity == Severity.WARNING
    assert any(a["fault_type"] == "SENSOR_FAULT" for a in res.alternatives)
    assert has_line(res, "Partial diagnosis active — required sensor: coolant_temp_c missing")


def test_safeguard_two_sensors_allow_critical():
    res = ENGINE.diagnose(bump(nominal(), oil_temp_c=40, coolant_temp_c=25))
    assert res.fault_type == "OVERHEATING" and res.severity == Severity.CRITICAL


def test_safeguard_graceful_degradation_evidence_and_detection():
    r = bump(nominal(), vibration_g=0.9, egt_cyl_2=-180)
    del r["egt_cyl_3"], r["injection_timing_deg"], r["cht_cyl_1"]
    res = ENGINE.diagnose(r)
    assert res.fault_type == "VIBRATION_MISFIRE" and res.partial_diagnosis
    for s in ("egt_cyl_3", "injection_timing_deg", "cht_cyl_1"):
        assert has_line(res, f"Partial diagnosis active — required sensor: {s} missing")


def test_safeguard_no_partial_line_when_all_sensors_present():
    assert not has_line(ENGINE.diagnose(nominal()), "Partial diagnosis")


def test_normalization_and_scaler():
    assert ec.normalized_deviation(110, 100, 5) == pytest.approx(2.0)
    sc = ec.FeatureScaler().fit([{"oil_temp_c": 80.0}, {"oil_temp_c": 100.0}])
    assert sc.transform({"oil_temp_c": 90.0})["oil_temp_c"] == pytest.approx(0.0)
    assert not ec.is_valid_reading("oil_temp_c", math.nan)

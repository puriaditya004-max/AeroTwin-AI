from app.risk_logic import (
    calculate_risk_level,
    calculate_health_status,
    calculate_trend,
)


def test_low_risk():
    assert calculate_risk_level(150) == "LOW"


def test_medium_risk():
    assert calculate_risk_level(75) == "MEDIUM"


def test_high_risk():
    assert calculate_risk_level(40) == "HIGH"


def test_critical_risk():
    assert calculate_risk_level(15) == "CRITICAL"


def test_good_health():
    assert calculate_health_status(0.90) == "GOOD"


def test_degraded_health():
    assert calculate_health_status(0.70) == "DEGRADED"


def test_poor_health():
    assert calculate_health_status(0.50) == "POOR"


def test_critical_health():
    assert calculate_health_status(0.20) == "CRITICAL"


def test_improving_trend():
    assert calculate_trend(160, 140) == "IMPROVING"


def test_degrading_trend():
    assert calculate_trend(120, 140) == "DEGRADING"


def test_stable_trend():
    assert calculate_trend(140, 142) == "STABLE"
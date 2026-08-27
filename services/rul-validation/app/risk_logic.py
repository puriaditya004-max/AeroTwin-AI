# =========================================================
# M5 - RUL Trend & Risk Logic
# =========================================================

from typing import Literal


RiskLevel = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]


def calculate_risk_level(
    predicted_rul: float,
) -> RiskLevel:
    """
    Convert predicted RUL into a risk level.

    RUL thresholds:
        > 100  -> LOW
        51-100 -> MEDIUM
        21-50  -> HIGH
        <= 20  -> CRITICAL
    """

    if predicted_rul > 100:
        return "LOW"

    if predicted_rul > 50:
        return "MEDIUM"

    if predicted_rul > 20:
        return "HIGH"

    return "CRITICAL"


def calculate_health_status(
    health_index: float,
) -> str:
    """
    Convert health index into a health status.
    """

    if health_index >= 0.8:
        return "GOOD"

    if health_index >= 0.6:
        return "DEGRADED"

    if health_index >= 0.4:
        return "POOR"

    return "CRITICAL"


def calculate_trend(
    current_rul: float,
    previous_rul: float,
) -> str:
    """
    Determine RUL trend using current and previous prediction.
    """

    difference = current_rul - previous_rul

    if difference > 5:
        return "IMPROVING"

    if difference < -5:
        return "DEGRADING"

    return "STABLE"
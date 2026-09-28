"""Discrete per-subsystem categorisation derived by M2.

Classifies thermal, lubrication, combustion, and vibration states into
demonstrator categories using context-adjusted deviations and physical margins.
"""

from typing import Optional

from app.contracts import (
    CombustionState,
    DerivedFeatures,
    LubricationState,
    Margins,
    OverallState,
    Sensors,
    SubsystemState,
    ThermalState,
    VibrationState,
)
from app.settings import EngineProfile


def classify_subsystems(
    sensors: Sensors,
    margins: Margins,
    derived: DerivedFeatures,
    profile: Optional[EngineProfile] = None,
) -> SubsystemState:
    reasons: list[str] = []

    # 1. Thermal State
    thermal: ThermalState = "normal"
    if margins.tempMarginC <= 0 or (derived.oilTempDeviationC is not None and derived.oilTempDeviationC > 25.0):
        thermal = "critical"
        reasons.append("CRITICAL_THERMAL_EXCURSION")
    elif margins.tempMarginC < 25.0 or (derived.oilTempDeviationC is not None and derived.oilTempDeviationC > 8.0) or (derived.coolantTempDeviationC is not None and derived.coolantTempDeviationC > 8.0):
        thermal = "elevated"
        reasons.append("ELEVATED_THERMAL_STATE")

    # 2. Lubrication State
    lubrication: LubricationState = "healthy"
    if margins.pressureMarginKpa <= 0 or (derived.oilPressureDeviationKpa is not None and derived.oilPressureDeviationKpa < -50.0):
        lubrication = "critical"
        reasons.append("CRITICAL_OIL_PRESSURE_DROP")
    elif margins.pressureMarginKpa < 25.0 or (derived.oilPressureDeviationKpa is not None and derived.oilPressureDeviationKpa < -25.0):
        lubrication = "degraded"
        reasons.append("DEGRADED_LUBRICATION")

    # 3. Combustion State
    combustion: CombustionState = "stable"
    if (derived.egtSpreadC is not None and derived.egtSpreadC > 45.0) or (derived.chtSpreadC is not None and derived.chtSpreadC > 30.0):
        combustion = "unstable"
        reasons.append("UNSTABLE_COMBUSTION_SPREAD")

    # 4. Vibration State
    vibration: VibrationState = "normal"
    if margins.vibrationMarginMmS <= 0 or (derived.vibrationDeviationMmS is not None and derived.vibrationDeviationMmS > 4.0):
        vibration = "severe"
        reasons.append("SEVERE_VIBRATION_EXCURSION")
    elif margins.vibrationMarginMmS < 5.0 or (derived.vibrationDeviationMmS is not None and derived.vibrationDeviationMmS > 2.0):
        vibration = "elevated"
        reasons.append("ELEVATED_VIBRATION")

    # 5. Overall State
    if thermal == "critical" or lubrication == "critical" or vibration == "severe":
        overall: OverallState = "critical"
    elif thermal == "elevated" or lubrication == "degraded" or combustion == "unstable" or vibration == "elevated":
        overall = "degraded"
    else:
        overall = "nominal"

    basis = "context-baseline" if any(
        d is not None for d in (derived.oilTempDeviationC, derived.oilPressureDeviationKpa, derived.vibrationDeviationMmS)
    ) else "absolute-limits"

    return SubsystemState(
        thermalState=thermal,
        lubricationState=lubrication,
        combustionState=combustion,
        vibrationState=vibration,
        overallState=overall,
        basis=basis,
        reasons=reasons,
    )

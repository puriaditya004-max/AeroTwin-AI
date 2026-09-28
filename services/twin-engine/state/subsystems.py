"""Discrete subsystem-state categorisation for M2.

Turns the continuous, environment-aware deviations and engine-profile margins
into the coarse states the operator HMI and downstream services consume:

    thermalState      normal   | elevated | critical
    lubricationState  healthy  | degraded | critical
    combustionState   stable   | unstable
    vibrationState    normal   | elevated | severe
    overallState      nominal  | degraded | critical

Design rules (documented demonstrator heuristics, not certified limits):

* When M2's context-adjusted deviations are available they decide the
  "elevated / degraded" band, so a hot-day or high-load reading that is
  normal *for that operating point* is not flagged.  Absolute warning limits
  are only used as a fallback when no deviation baseline exists.
* "critical / severe" is decided by absolute engine-profile limits and is
  never softened by context — a critical limit is critical anywhere.
* The elevated/degraded deviation thresholds intentionally match the M4
  fusion corroboration gates (oil/coolant > +8 C, oil pressure < -25 kPa,
  vibration > +2 mm/s) so M2's state and M4's fault claims agree.
"""

from app.contracts import DerivedFeatures, Margins, Sensors, SubsystemState
from app.settings import EngineProfile

# Deviation bands (actual - expected).
THERMAL_ELEVATED_DEV_C = 8.0
LUBRICATION_DEGRADED_DEV_KPA = -25.0
LUBRICATION_CRITICAL_DEV_KPA = -60.0
VIBRATION_ELEVATED_DEV_MM_S = 2.0
VIBRATION_SEVERE_DEV_MM_S = 6.0

# Combustion-stability indicators.
CHT_SPREAD_UNSTABLE_C = 40.0
EGT_SPREAD_UNSTABLE_C = 60.0
VIBRATION_JITTER_UNSTABLE_MM_S = 1.5


def _thermal(sensors: Sensors, margins: Margins, derived: DerivedFeatures, profile: EngineProfile,
             reasons: list[str]) -> tuple[str, bool]:
    temp = profile.temperature
    cht_max = max(sensors.chtCylindersC) if sensors.chtCylindersC else None
    egt_max = max(sensors.egtCylindersC) if sensors.egtCylindersC else None

    if (
        sensors.oilTempC >= temp["oilCriticalC"]
        or sensors.coolantTempC >= temp["coolantCriticalC"]
        or (cht_max is not None and cht_max >= temp["chtCriticalC"])
        or (egt_max is not None and egt_max >= temp["egtCriticalC"])
        or margins.tempMarginC <= 0
    ):
        reasons.append("THERMAL_CRITICAL_LIMIT")
        return "critical", True

    deviations = [d for d in (derived.oilTempDeviationC, derived.coolantTempDeviationC) if d is not None]
    if deviations:
        if max(deviations) > THERMAL_ELEVATED_DEV_C:
            reasons.append("THERMAL_ABOVE_CONTEXT_BASELINE")
            return "elevated", True
        return "normal", True

    # Fallback: no deviation baseline available -> absolute warning limits.
    if (
        sensors.oilTempC >= temp["oilWarningC"]
        or sensors.coolantTempC >= temp["coolantWarningC"]
        or (cht_max is not None and cht_max >= temp["chtWarningC"])
        or (egt_max is not None and egt_max >= temp["egtWarningC"])
    ):
        reasons.append("THERMAL_ABOVE_WARNING_LIMIT")
        return "elevated", False
    return "normal", False


def _lubrication(sensors: Sensors, margins: Margins, derived: DerivedFeatures, profile: EngineProfile,
                 reasons: list[str]) -> tuple[str, bool]:
    pressure = profile.pressure
    dev = derived.oilPressureDeviationKpa

    if margins.pressureMarginKpa < 0 or (dev is not None and dev <= LUBRICATION_CRITICAL_DEV_KPA):
        reasons.append("OIL_PRESSURE_CRITICAL")
        return "critical", True

    if sensors.oilPressureKpa > pressure["oilMaxKpa"]:
        reasons.append("OIL_PRESSURE_ABOVE_MAX")
        return "degraded", dev is not None

    if dev is not None:
        if dev < LUBRICATION_DEGRADED_DEV_KPA:
            reasons.append("OIL_PRESSURE_BELOW_CONTEXT_BASELINE")
            return "degraded", True
        return "healthy", True

    # Fallback: thin margin over the load-adjusted minimum.
    if margins.pressureMarginKpa < 20.0:
        reasons.append("OIL_PRESSURE_LOW_MARGIN")
        return "degraded", False
    return "healthy", False


def _combustion(sensors: Sensors, derived: DerivedFeatures, profile: EngineProfile,
                reasons: list[str]) -> str:
    unstable = False
    if derived.chtSpreadC is not None and derived.chtSpreadC >= CHT_SPREAD_UNSTABLE_C:
        reasons.append("CHT_CYLINDER_SPREAD_HIGH")
        unstable = True
    if derived.egtSpreadC is not None and derived.egtSpreadC >= EGT_SPREAD_UNSTABLE_C:
        reasons.append("EGT_CYLINDER_SPREAD_HIGH")
        unstable = True
    timing_dev = derived.injectionTimingDeviationDeg
    if timing_dev is not None and abs(timing_dev) > profile.injection["toleranceDeg"]:
        reasons.append("INJECTION_TIMING_OUT_OF_TOLERANCE")
        unstable = True
    if derived.rollingStdVibration >= VIBRATION_JITTER_UNSTABLE_MM_S:
        reasons.append("VIBRATION_JITTER_HIGH")
        unstable = True
    return "unstable" if unstable else "stable"


def _vibration(sensors: Sensors, margins: Margins, derived: DerivedFeatures, profile: EngineProfile,
               reasons: list[str]) -> tuple[str, bool]:
    vib = profile.vibration
    dev = derived.vibrationDeviationMmS

    if margins.vibrationMarginMmS <= 0 or (dev is not None and dev >= VIBRATION_SEVERE_DEV_MM_S):
        reasons.append("VIBRATION_SEVERE")
        return "severe", True

    if dev is not None:
        if dev > VIBRATION_ELEVATED_DEV_MM_S:
            reasons.append("VIBRATION_ABOVE_CONTEXT_BASELINE")
            return "elevated", True
        return "normal", True

    if sensors.vibrationMmS >= vib["warningMmS"]:
        reasons.append("VIBRATION_ABOVE_WARNING_LIMIT")
        return "elevated", False
    return "normal", False


def classify_subsystems(
    sensors: Sensors,
    margins: Margins,
    derived: DerivedFeatures,
    profile: EngineProfile,
) -> SubsystemState:
    """Derive the discrete subsystem states for one TwinState."""
    reasons: list[str] = []
    thermal, thermal_ctx = _thermal(sensors, margins, derived, profile, reasons)
    lubrication, lube_ctx = _lubrication(sensors, margins, derived, profile, reasons)
    combustion = _combustion(sensors, derived, profile, reasons)
    vibration, vib_ctx = _vibration(sensors, margins, derived, profile, reasons)

    if thermal == "critical" or lubrication == "critical" or vibration == "severe":
        overall = "critical"
    elif (
        thermal == "elevated"
        or lubrication == "degraded"
        or combustion == "unstable"
        or vibration == "elevated"
    ):
        overall = "degraded"
    else:
        overall = "nominal"

    used_context = thermal_ctx and lube_ctx and vib_ctx
    return SubsystemState(
        thermalState=thermal,
        lubricationState=lubrication,
        combustionState=combustion,
        vibrationState=vibration,
        overallState=overall,
        basis="context-baseline" if used_context else "absolute-limits",
        reasons=reasons,
    )

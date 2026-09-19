"""
Gate 06: Quality-Aware Decision Fusion Policy

Combines TwinState quality flags, Isolation Forest anomaly score, and XGBoost classifier probabilities.
Enforces safety rules: degraded/stale data never yields unsupported physical fault claims.

Additive enrichment (M2/M4 module doc, "Fault contract enrichment"):
componentId/subsystem localization, human-readable evidence, severity, recommendedAction,
alternativePossibilities, requiresHumanConfirmation, operatingConditionOutOfRange, and an
active SENSOR_FAULT corroboration path. All new FaultPrediction fields are optional, so
existing M5/M6 consumers that only read the v1 fields are unaffected.
"""

from datetime import datetime, timezone
from typing import List, Optional
import numpy as np

from app.contracts import TwinState, FaultPrediction, FaultType, FaultSeverity, Contributor, StateQuality
from features.builder import FEATURE_NAMES


# Level-3 localization + operator guidance per fault type. These labels are
# demonstrator conventions (documented heuristics, not a certified parts
# catalogue) — see the M2/M4 module doc for the exact same mapping.
FAULT_COMPONENT_MAP = {
    FaultType.OVERHEATING: {
        "componentId": "cooling-system",
        "subsystem": "Cooling",
        "recommendedAction": "Inspect cooling system airflow and coolant/oil temperature sensors.",
        "alternativePossibilities": ["Temporary high-load or hot-ambient condition", "Temperature sensor drift"],
    },
    FaultType.OIL_PRESSURE_DEGRADATION: {
        "componentId": "oil-system",
        "subsystem": "Lubrication",
        "recommendedAction": "Inspect lubrication system and verify oil pressure sensor calibration.",
        "alternativePossibilities": ["Oil pressure sensor drift", "Temporary high-load condition"],
    },
    FaultType.VIBRATION_MISFIRE: {
        "componentId": "combustion-drivetrain",
        "subsystem": "Combustion / Vibration",
        "recommendedAction": "Inspect for misfire/imbalance; verify vibration sensor mounting.",
        "alternativePossibilities": ["Vibration sensor mounting looseness", "Transient throttle transient"],
    },
    FaultType.SENSOR_FAULT: {
        "componentId": "sensor-array",
        "subsystem": "Sensor Array",
        "recommendedAction": "Verify sensor wiring/calibration before trusting downstream health/RUL outputs.",
        "alternativePossibilities": ["Genuine engine fault masked by a failing sensor"],
    },
}

# Physically-implausible margin bounds used only to actively corroborate a
# SENSOR_FAULT classification (as opposed to just suppressing a claim to
# NONE). These are documented demonstrator heuristics, wider than any real
# fault scenario in the training data, chosen so only clearly bogus sensor
# readings trip them.
IMPLAUSIBLE_TEMP_MARGIN_C = (-40.0, 60.0)
IMPLAUSIBLE_PRESSURE_MARGIN_KPA = (-60.0, 150.0)
IMPLAUSIBLE_VIBRATION_MARGIN_MM_S = (-15.0, 30.0)

# reasonCodes emitted by M2 (state/environment.py) when altitude/ambient
# temperature fall outside the calibrated expected-value envelope.
OOD_REASON_CODES = {"OUT_OF_RANGE_ALTITUDE", "OUT_OF_RANGE_AMBIENT_TEMP"}


def _is_physically_implausible(latest_state: TwinState) -> bool:
    """True when raw margins fall outside any plausible physical range.

    This does not require a specific fault class — it only flags that the
    *reading itself* is implausible, which is stronger evidence of a sensor
    fault than a genuine engine condition.
    """
    margins = latest_state.margins
    low, high = IMPLAUSIBLE_TEMP_MARGIN_C
    if not (low <= margins.tempMarginC <= high):
        return True
    low, high = IMPLAUSIBLE_PRESSURE_MARGIN_KPA
    if not (low <= margins.pressureMarginKpa <= high):
        return True
    low, high = IMPLAUSIBLE_VIBRATION_MARGIN_MM_S
    if not (low <= margins.vibrationMarginMmS <= high):
        return True
    return False


def _build_evidence(fault_type: FaultType, derived, margins) -> List[str]:
    """Human-readable evidence lines, in addition to the raw SHAP contributors."""
    lines: List[str] = []
    if fault_type == FaultType.OVERHEATING:
        if derived.oilTempDeviationC is not None and derived.oilTempDeviationC > 8.0:
            lines.append(
                f"Oil temperature {derived.oilTempDeviationC:+.1f} C above the context-adjusted baseline"
            )
        if derived.coolantTempDeviationC is not None and derived.coolantTempDeviationC > 8.0:
            lines.append(
                f"Coolant temperature {derived.coolantTempDeviationC:+.1f} C above the context-adjusted baseline"
            )
    elif fault_type == FaultType.OIL_PRESSURE_DEGRADATION:
        if derived.oilPressureDeviationKpa is not None:
            lines.append(
                f"Oil pressure {derived.oilPressureDeviationKpa:+.1f} kPa below the context-adjusted baseline"
            )
    elif fault_type == FaultType.VIBRATION_MISFIRE:
        if derived.vibrationDeviationMmS is not None:
            lines.append(
                f"Vibration {derived.vibrationDeviationMmS:+.2f} mm/s above the context-adjusted baseline"
            )
    elif fault_type == FaultType.SENSOR_FAULT:
        lines.append("Reported margin(s) fall outside any physically plausible range for this engine profile")
    if not lines and fault_type != FaultType.NONE:
        # Deviation baseline unavailable (v1 telemetry) — fall back to raw margins.
        lines.append(
            f"Margins at detection: temp={margins.tempMarginC:.1f}C, "
            f"pressure={margins.pressureMarginKpa:.1f}kPa, vibration={margins.vibrationMarginMmS:.1f}mm/s"
        )
    return lines


def _severity_for(confidence: float, anomaly_score: float) -> FaultSeverity:
    if confidence >= 0.85 and anomaly_score >= 0.70:
        return FaultSeverity.CRITICAL
    if confidence >= 0.70:
        return FaultSeverity.HIGH
    if confidence >= 0.60:
        return FaultSeverity.WARNING
    return FaultSeverity.INFO


class DecisionFusionPolicy:
    """Quality-aware fusion policy manager."""

    def __init__(
        self,
        anomaly_threshold: float = 0.55,
        confidence_threshold: float = 0.60
    ):
        self.anomaly_threshold = anomaly_threshold
        self.confidence_threshold = confidence_threshold

    def fuse(
        self,
        latest_state: TwinState,
        anomaly_score: float,
        predicted_type: FaultType,
        confidence: float,
        contributors: List[Contributor]
    ) -> FaultPrediction:
        """
        Fuses inputs according to quality and confidence safety gates.
        """
        derived = latest_state.derivedFeatures
        reason_codes = set(getattr(derived, "reasonCodes", None) or [])
        ood = bool(reason_codes & OOD_REASON_CODES)

        # Safety rule: Degraded or Stale state quality prevents physical fault claims
        if latest_state.stateQuality in (StateQuality.STALE, StateQuality.DEGRADED):
            return FaultPrediction(
                engineId=latest_state.engineId,
                missionId=latest_state.missionId,
                correlationId=latest_state.correlationId,
                predictionTime=datetime.now(timezone.utc),
                producerVersion="m4-fault@1.2.0-enriched",
                faultType=FaultType.NONE,
                confidence=0.0,
                anomalyScore=float(anomaly_score),
                contributors=[],
                detectionDelayMs=None,
                evidence=["State quality is DEGRADED/STALE — suppressing any physical fault claim"],
                requiresHumanConfirmation=False,
                operatingConditionOutOfRange=ood,
            )

        final_fault = predicted_type
        final_conf = confidence
        # Integration regression: nominal oil-temperature jitter was classified as
        # overheating by the committed model. For measured M2 inputs, require
        # independent physical support before surfacing a physical-fault claim.
        # This only suppresses unsupported classes; it never fabricates a new one.
        sensors = (latest_state.model_extra or {}).get("sensors")
        has_context_baseline = any(
            value is not None
            for value in (
                derived.oilTempDeviationC,
                derived.coolantTempDeviationC,
                derived.oilPressureDeviationKpa,
                derived.vibrationDeviationMmS,
            )
        )
        if has_context_baseline:
            # M2's environment-aware baseline is authoritative when present.
            # The bounds are demonstrator safety gates: they corroborate a
            # classifier result, but never create a fault on their own.
            supported = {
                FaultType.OVERHEATING: (
                    (derived.oilTempDeviationC is not None and derived.oilTempDeviationC > 8.0)
                    or (derived.coolantTempDeviationC is not None and derived.coolantTempDeviationC > 8.0)
                ),
                FaultType.OIL_PRESSURE_DEGRADATION: (
                    derived.oilPressureDeviationKpa is not None
                    and derived.oilPressureDeviationKpa < -25.0
                ),
                FaultType.VIBRATION_MISFIRE: (
                    derived.vibrationDeviationMmS is not None
                    and derived.vibrationDeviationMmS > 2.0
                ),
            }
            if final_fault in supported and not supported[final_fault]:
                if _is_physically_implausible(latest_state):
                    # Not corroborated by the environment-aware baseline AND the raw
                    # reading itself is out of any plausible range: more likely a
                    # sensor fault than a genuine engine condition, so surface that
                    # instead of silently dropping to NONE.
                    final_fault = FaultType.SENSOR_FAULT
                    final_conf = max(final_conf, 0.60)
                else:
                    final_fault = FaultType.NONE
                    final_conf = 0.0
                    contributors = []
        elif sensors:
            supported = {
                FaultType.OVERHEATING: latest_state.margins.tempMarginC < 25
                    or sensors["oilTempC"] > 115 or sensors["coolantTempC"] > 110,
                FaultType.OIL_PRESSURE_DEGRADATION: latest_state.margins.pressureMarginKpa < 0,
                FaultType.VIBRATION_MISFIRE: latest_state.margins.vibrationMarginMmS < 4,
            }
            if final_fault in supported and not supported[final_fault]:
                if _is_physically_implausible(latest_state):
                    final_fault = FaultType.SENSOR_FAULT
                    final_conf = max(final_conf, 0.60)
                else:
                    final_fault = FaultType.NONE
                    final_conf = 0.0
                    contributors = []

        # A physically implausible reading always at least raises a sensor-fault
        # possibility, even when the classifier's own prediction was NONE.
        if final_fault == FaultType.NONE and _is_physically_implausible(latest_state):
            final_fault = FaultType.SENSOR_FAULT
            final_conf = max(final_conf, 0.55)
            contributors = []

        # Physical fault claim requires calibrated classifier confidence + supporting anomaly score
        if final_fault not in (FaultType.NONE, FaultType.SENSOR_FAULT):
            if final_conf < self.confidence_threshold or anomaly_score < (self.anomaly_threshold * 0.5):
                # Downgrade to NONE if confidence or supporting anomaly evidence is insufficient
                final_fault = FaultType.NONE
                final_conf = 1.0 - final_conf

        component = FAULT_COMPONENT_MAP.get(final_fault)
        evidence = _build_evidence(final_fault, derived, latest_state.margins) if final_fault != FaultType.NONE else []
        if ood and final_fault != FaultType.NONE:
            evidence.append("Operating condition (altitude/ambient temperature) outside M2's calibrated envelope — confidence reduced")
            final_conf = round(final_conf * 0.85, 3)

        return FaultPrediction(
            engineId=latest_state.engineId,
            missionId=latest_state.missionId,
            correlationId=latest_state.correlationId,
            predictionTime=datetime.now(timezone.utc),
            producerVersion="m4-fault@1.2.0-enriched",
            faultType=final_fault,
            confidence=float(final_conf),
            anomalyScore=float(anomaly_score),
            contributors=contributors,
            detectionDelayMs=None,
            componentId=component["componentId"] if component else None,
            subsystem=component["subsystem"] if component else None,
            severity=_severity_for(final_conf, anomaly_score) if final_fault != FaultType.NONE else None,
            evidence=evidence,
            recommendedAction=component["recommendedAction"] if component else None,
            alternativePossibilities=component["alternativePossibilities"] if component else [],
            requiresHumanConfirmation=final_fault != FaultType.NONE,
            operatingConditionOutOfRange=ood,
        )

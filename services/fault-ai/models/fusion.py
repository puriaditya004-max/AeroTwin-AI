"""M4 fault fusion with accuracy safeguards.

Safeguards
----------
1. Multi-sensor evidence rule: CRITICAL requires >= 2 correlated, valid sensors abnormal.
   A single (unverifiable) sensor is capped at WARNING.
2. Graceful degradation: missing/dropped key sensors add
   "Partial diagnosis active — required sensor: <SENSOR_NAME> missing" to the evidence.
3. Multi-fault handling: simultaneous faults are reported as separate findings (primary +
   alternatives, all captured in evidence); nothing is merged or dropped.
4. Sensor faults: dropout (invalid value) or isolated drift (deviation with all correlated
   peers nominal) -> SENSOR_FAULT, excluded from mechanical-fault fusion.
5. Transients (throttle steps) widen tolerances and cap severity at HIGH.
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Dict, List, Mapping, Optional


def load_environment_compensation():
    """Import the shared package (its directory name contains a hyphen, so load by path if needed)."""
    try:
        import environment_compensation as ec  # installed / on PYTHONPATH under an importable name
        return ec
    except ImportError:
        pass
    pkg_dir = Path(__file__).resolve().parents[3] / "packages" / "environment-compensation"
    spec = importlib.util.spec_from_file_location(
        "environment_compensation", pkg_dir / "__init__.py", submodule_search_locations=[str(pkg_dir)]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["environment_compensation"] = mod
    spec.loader.exec_module(mod)
    return mod


ec = load_environment_compensation()


class Severity(IntEnum):
    NORMAL = 0
    INFO = 1
    WARNING = 2
    HIGH = 3
    CRITICAL = 4


Z_ABNORMAL = 3.0
Z_SEVERE = 5.0
N_CYL = ec.operating_point.N_CYLINDERS
CHT = [f"cht_cyl_{i}" for i in range(1, N_CYL + 1)]
EGT = [f"egt_cyl_{i}" for i in range(1, N_CYL + 1)]

ENGINE_FAULTS = ("OVERHEATING", "OIL_PRESSURE_DEGRADATION", "VIBRATION_MISFIRE")

# fault -> {sensor or prefix_: expected direction (+1 high, -1 low, 0 either)}
FAULT_SIGNATURES: Dict[str, Dict[str, int]] = {
    "OVERHEATING": {"oil_temp_c": 1, "coolant_temp_c": 1, "cht_cyl_": 1},
    "OIL_PRESSURE_DEGRADATION": {"oil_pressure_psi": -1, "oil_pressure_kpa": -1, "oil_temp_c": 1, "vibration_g": 1, "vibration_mm_s": 1},
    "VIBRATION_MISFIRE": {"vibration_g": 1, "vibration_mm_s": 1, "egt_cyl_": 0, "injection_timing_deg": 0},
}
ANCHORS = {"OIL_PRESSURE_DEGRADATION": {"oil_pressure_psi", "oil_pressure_kpa"}}
FAULT_REQUIRED = {
    "OVERHEATING": ["oil_temp_c", "coolant_temp_c", *CHT],
    "OIL_PRESSURE_DEGRADATION": ["oil_pressure_psi", "oil_temp_c", "vibration_g"],
    "VIBRATION_MISFIRE": ["vibration_g", *EGT, "injection_timing_deg"],
}
KEY_SENSORS = ["oil_temp_c", "oil_pressure_psi", "coolant_temp_c", "vibration_g", *CHT, *EGT, "injection_timing_deg"]

# Correlated peers used to tell a real fault from a drifting/dropped sensor.
PEERS: Dict[str, List[str]] = {
    "oil_temp_c": ["coolant_temp_c", *CHT, "oil_pressure_psi"],
    "coolant_temp_c": ["oil_temp_c", *CHT],
    "oil_pressure_psi": ["oil_temp_c", "vibration_g"],
    "oil_pressure_kpa": ["oil_temp_c", "vibration_mm_s"],
    "vibration_g": [*EGT, "injection_timing_deg"],
    "vibration_mm_s": [*EGT, "injection_timing_deg"],
    "injection_timing_deg": ["vibration_g", "vibration_mm_s", *EGT],
}
for _i in range(N_CYL):
    PEERS[CHT[_i]] = ["oil_temp_c", "coolant_temp_c", *[c for c in CHT if c != CHT[_i]]]
    PEERS[EGT[_i]] = [CHT[_i], "vibration_g", "vibration_mm_s", "injection_timing_deg"]


@dataclass
class FaultFinding:
    fault_type: str
    component: str
    severity: Severity
    confidence: float
    evidence: List[str]
    sensors: List[str] = field(default_factory=list)


@dataclass
class FusionResult:
    fault_type: str
    component: str
    severity: Severity
    confidence: float
    evidence: List[str]
    alternatives: List[dict]
    findings: List[FaultFinding]
    partial_diagnosis: bool = False
    operating_phase: str = "CRUISE"
    transient: bool = False

    def to_dict(self) -> dict:
        return {
            "fault_type": self.fault_type, "component": self.component, "severity": self.severity.name,
            "confidence": round(self.confidence, 3), "evidence": list(self.evidence),
            "alternatives": list(self.alternatives), "partial_diagnosis": self.partial_diagnosis,
            "operating_phase": self.operating_phase, "transient": self.transient,
        }


def _direction(fault: str, sensor: str) -> Optional[int]:
    for key, d in FAULT_SIGNATURES[fault].items():
        if sensor == key or (key.endswith("_") and sensor.startswith(key)):
            return d
    return None


def _matches(z: float, direction: int) -> bool:
    if direction > 0:
        return z >= Z_ABNORMAL
    if direction < 0:
        return z <= -Z_ABNORMAL
    return abs(z) >= Z_ABNORMAL


def _cyl(sensor: str) -> str:
    return sensor.rsplit("_", 1)[1]


class FaultFusionEngine:
    """Fuses per-sensor deviations from context-aware baselines into fault findings."""

    def diagnose(self, readings: Mapping[str, Optional[float]], context: Optional[Mapping[str, float]] = None) -> FusionResult:
        ctx = dict(context or {})
        pa = float(ctx.get("altitude_ft", 0.0))
        oat = ctx.get("oat_c")
        oat = ec.altitude_model.isa_temperature_c(pa) if oat is None else float(oat)

        op = ec.build_operating_point(readings, ctx)
        expected = ec.expected_baselines(op, pa, oat)
        tol = ec.ambient_model.thermal_tolerance_scale(oat)

        sigma: Dict[str, float] = {}
        for s in expected:
            scale = ec.transient_sigma_scale(s) if op.transient else 1.0
            if ec.is_thermal_sensor(s):
                scale *= tol
            sigma[s] = ec.sensor_sigma(s) * scale

        valid = {s: float(v) for s, v in readings.items() if s in expected and ec.is_valid_reading(s, v)}
        invalid = [s for s, v in readings.items() if s in expected and not ec.is_valid_reading(s, v)]
        devs = ec.deviation_report(valid, expected, sigma)
        abnormal = {s: d for s, d in devs.items() if abs(d.z) >= Z_ABNORMAL}

        # --- sensor faults: dropout + isolated drift ------------------------------------------------
        sensor_findings: List[FaultFinding] = []
        suspects = set()
        unverified = set()
        for s in invalid:
            sensor_findings.append(FaultFinding(
                "SENSOR_FAULT", s, Severity.WARNING, 0.9,
                [f"{s} reading invalid or dropped out ({readings.get(s)!r}) — excluded from fusion"], [s]))
        for s, d in abnormal.items():
            if s not in PEERS:
                continue
            avail = [p for p in PEERS[s] if p in devs]
            if not avail:
                unverified.add(s)
            elif not any(p in abnormal for p in avail):
                suspects.add(s)
                sensor_findings.append(FaultFinding(
                    "SENSOR_FAULT", s, Severity.WARNING, 0.8,
                    [f"{s} deviates {d.z:+.1f} sigma (actual {d.actual:.1f}, expected {d.expected:.1f}) but "
                     f"correlated sensors are nominal — suspected drift; excluded from fusion"], [s]))

        # --- mechanical fault fusion (valid, non-suspect sensors only) --------------------------------
        active = {s: d for s, d in abnormal.items() if s not in suspects}
        missing = [s for s in KEY_SENSORS if s not in valid]
        engine_findings = self._engine_findings(active, unverified, missing, op.transient)

        findings = engine_findings + sensor_findings
        evidence_sys: List[str] = []
        if op.transient:
            evidence_sys.append(
                f"Transient condition ({op.phase.value}, throttle rate {op.throttle_rate_pct_s:.1f} %/s) — "
                f"tolerances widened; short-term deviations not treated as permanent faults")
        evidence_sys += [f"Partial diagnosis active — required sensor: {s} missing" for s in missing]

        if not findings:
            return FusionResult("NORMAL", "none", Severity.NORMAL, 0.95, evidence_sys, [], [],
                                bool(missing), op.phase.value, op.transient)

        findings.sort(key=lambda f: (f.severity, f.confidence), reverse=True)
        primary = findings[0]
        multi = len(findings) > 1
        evidence: List[str] = []
        for f in findings:
            evidence += [f"[{f.fault_type}] {e}" if multi else e for e in f.evidence]
        if multi:
            evidence += [f"Concurrent finding retained: {f.fault_type} on {f.component} ({f.severity.name})"
                         for f in findings[1:]]
        evidence += evidence_sys

        alternatives = [{"fault_type": f.fault_type, "component": f.component, "severity": f.severity.name,
                         "confidence": round(f.confidence, 3), "sensors": f.sensors} for f in findings[1:]]
        if primary.fault_type in ENGINE_FAULTS and primary.severity <= Severity.WARNING and set(primary.sensors) & unverified:
            alternatives.append({"fault_type": "SENSOR_FAULT", "component": primary.sensors[0],
                                 "severity": "WARNING", "confidence": 0.3, "sensors": primary.sensors,
                                 "reason": "single uncorroborated sensor — cannot rule out sensor fault"})
        return FusionResult(primary.fault_type, primary.component, primary.severity, primary.confidence,
                            evidence, alternatives, findings, bool(missing), op.phase.value, op.transient)

    # ------------------------------------------------------------------------------------------------
    def _engine_findings(self, active, unverified, missing, transient) -> List[FaultFinding]:
        findings: List[FaultFinding] = []
        consumed = set()
        for fault in FAULT_SIGNATURES:
            sensors = [s for s, d in active.items()
                       if (dr := _direction(fault, s)) is not None and _matches(d.z, dr)]
            anchors = ANCHORS.get(fault)
            if anchors and not anchors & set(sensors):
                continue
            if len(sensors) >= 2:
                findings.append(self._build(fault, sensors, active, missing, transient))
                consumed |= set(sensors)
        for s, d in active.items():
            if s in consumed:
                continue
            for fault in FAULT_SIGNATURES:
                dr = _direction(fault, s)
                if dr is not None and _matches(d.z, dr):
                    findings.append(self._build(fault, [s], active, missing, transient))
                    break
        return findings

    def _build(self, fault, sensors, active, missing, transient) -> FaultFinding:
        n = len(sensors)
        max_z = max(abs(active[s].z) for s in sensors)
        evidence = [f"{s}: actual {active[s].actual:.1f} vs expected {active[s].expected:.1f} (z={active[s].z:+.1f})"
                    for s in sorted(sensors, key=lambda x: -abs(active[x].z))]
        if n >= 2:
            sev = Severity.CRITICAL if max_z >= Z_SEVERE else Severity.HIGH
            evidence.insert(0, f"Multi-sensor evidence: {n} correlated sensors abnormal")
            conf = min(0.99, 0.55 + 0.07 * min(n, 5) + 0.02 * min(max_z, 10.0))
        else:
            sev = Severity.WARNING
            evidence.insert(0, "Severity capped at WARNING — only 1 abnormal sensor (multi-sensor evidence rule)")
            conf = min(0.6, 0.4 + 0.02 * min(max_z, 10.0))
        if transient and sev > Severity.HIGH:
            sev = Severity.HIGH
            evidence.append("Severity capped at HIGH during throttle transient")
        req = FAULT_REQUIRED[fault]
        miss_frac = sum(1 for s in req if s in missing) / len(req)
        conf *= 1.0 - 0.4 * miss_frac
        return FaultFinding(fault, self._component(fault, sensors, active), sev, conf, evidence, list(sensors))

    @staticmethod
    def _component(fault, sensors, active) -> str:
        top = max(sensors, key=lambda s: abs(active[s].z))
        if fault == "OVERHEATING":
            if top.startswith("cht_cyl_"):
                return f"cylinder_{_cyl(top)}_head"
            return "cooling_system" if top == "coolant_temp_c" else "oil_system"
        if fault == "OIL_PRESSURE_DEGRADATION":
            return "oil_pump"
        egt = [s for s in sensors if s.startswith("egt_cyl_")]
        if egt:
            return f"cylinder_{_cyl(max(egt, key=lambda s: abs(active[s].z)))}"
        return "injection_system" if "injection_timing_deg" in sensors else "combustion"


_ENGINE = FaultFusionEngine()


def diagnose(readings, context=None) -> FusionResult:
    """Module-level convenience wrapper."""
    return _ENGINE.diagnose(readings, context)


# ---------------------------------------------------------------------------
# DecisionFusionPolicy for Pydantic runtime compatibility
# ---------------------------------------------------------------------------
from datetime import datetime, timezone
from app.contracts import TwinState, FaultPrediction, FaultType, FaultSeverity, Contributor, StateQuality

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

IMPLAUSIBLE_TEMP_MARGIN_C = (-40.0, 60.0)
IMPLAUSIBLE_PRESSURE_MARGIN_KPA = (-60.0, 150.0)
IMPLAUSIBLE_VIBRATION_MARGIN_MM_S = (-15.0, 30.0)
OOD_REASON_CODES = {"OUT_OF_RANGE_ALTITUDE", "OUT_OF_RANGE_AMBIENT_TEMP"}


def _is_physically_implausible(latest_state: TwinState) -> bool:
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


def _build_pydantic_evidence(fault_type: FaultType, derived, margins) -> List[str]:
    lines: List[str] = []
    if fault_type == FaultType.OVERHEATING:
        if derived.oilTempDeviationC is not None and derived.oilTempDeviationC > 8.0:
            lines.append(f"Oil temperature {derived.oilTempDeviationC:+.1f} C above the context-adjusted baseline")
        if derived.coolantTempDeviationC is not None and derived.coolantTempDeviationC > 8.0:
            lines.append(f"Coolant temperature {derived.coolantTempDeviationC:+.1f} C above the context-adjusted baseline")
    elif fault_type == FaultType.OIL_PRESSURE_DEGRADATION:
        if derived.oilPressureDeviationKpa is not None:
            lines.append(f"Oil pressure {derived.oilPressureDeviationKpa:+.1f} kPa below the context-adjusted baseline")
    elif fault_type == FaultType.VIBRATION_MISFIRE:
        if derived.vibrationDeviationMmS is not None:
            lines.append(f"Vibration {derived.vibrationDeviationMmS:+.2f} mm/s above the context-adjusted baseline")
    elif fault_type == FaultType.SENSOR_FAULT:
        lines.append("Reported margin(s) fall outside any physically plausible range for this engine profile")
    if not lines and fault_type != FaultType.NONE:
        lines.append(f"Margins at detection: temp={margins.tempMarginC:.1f}C, pressure={margins.pressureMarginKpa:.1f}kPa, vibration={margins.vibrationMarginMmS:.1f}mm/s")
    return lines


def _severity_for_pydantic(confidence: float, anomaly_score: float) -> FaultSeverity:
    if confidence >= 0.85 and anomaly_score >= 0.70:
        return FaultSeverity.CRITICAL
    if confidence >= 0.70:
        return FaultSeverity.HIGH
    if confidence >= 0.60:
        return FaultSeverity.WARNING
    return FaultSeverity.INFO


class DecisionFusionPolicy:
    def __init__(self, anomaly_threshold: float = 0.55, confidence_threshold: float = 0.60):
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
        derived = latest_state.derivedFeatures
        reason_codes = set(getattr(derived, "reasonCodes", None) or [])
        ood = bool(reason_codes & OOD_REASON_CODES)

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
                    final_fault = FaultType.SENSOR_FAULT
                    final_conf = max(final_conf, 0.60)
                else:
                    final_fault = FaultType.NONE
                    final_conf = 0.0
                    contributors = []
        elif sensors:
            supported = {
                FaultType.OVERHEATING: latest_state.margins.tempMarginC < 25
                    or sensors.get("oilTempC", 0) > 115 or sensors.get("coolantTempC", 0) > 110,
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

        if final_fault == FaultType.NONE and _is_physically_implausible(latest_state):
            final_fault = FaultType.SENSOR_FAULT
            final_conf = max(final_conf, 0.55)
            contributors = []

        if final_fault not in (FaultType.NONE, FaultType.SENSOR_FAULT):
            if final_conf < self.confidence_threshold or anomaly_score < (self.anomaly_threshold * 0.5):
                final_fault = FaultType.NONE
                final_conf = 1.0 - final_conf

        component = FAULT_COMPONENT_MAP.get(final_fault)
        evidence = _build_pydantic_evidence(final_fault, derived, latest_state.margins) if final_fault != FaultType.NONE else []
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
            severity=_severity_for_pydantic(final_conf, anomaly_score) if final_fault != FaultType.NONE else None,
            evidence=evidence,
            recommendedAction=component["recommendedAction"] if component else None,
            alternativePossibilities=component["alternativePossibilities"] if component else [],
            requiresHumanConfirmation=final_fault != FaultType.NONE,
            operatingConditionOutOfRange=ood,
        )

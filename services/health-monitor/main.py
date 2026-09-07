"""Canonical boundary using M2 profile margins and original M3 score weights."""
import sys
from pathlib import Path
from fastapi import FastAPI
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/schemas/python"))
from contracts import TwinState as TwinStateInput, HealthSnapshot, SubScores

class PhysicsHealthEngine:
    def evaluate_health(self, state: TwinStateInput) -> HealthSnapshot:
        rules, reasons = [], []
        temp, pressure, vibration, quality = 30.0, 30.0, 25.0, 15.0
        data_issue = state.stateQuality != "GOOD"
        if data_issue:
            quality = 5.0
            reasons.append("SENSOR_DATA_DEGRADED")
        else:
            # M2 uses 230 C critical / 205 C warning and 12 / 8 mm/s.
            sensors = (state.model_extra or {}).get("sensors", {})
            critical = state.margins.tempMarginC < 0 or sensors.get("oilTempC", 0) > 130 or sensors.get("coolantTempC", 0) > 120
            warning = state.margins.tempMarginC < 25 or sensors.get("oilTempC", 0) > 115 or sensors.get("coolantTempC", 0) > 110
            if critical:
                temp = 5.0
                rules.append("RULE_TEMP_CRITICAL")
                reasons.append("CRITICAL_ENGINE_OVERHEATING")
            elif warning:
                temp = 18.0
                rules.append("RULE_TEMP_WARN")
                reasons.append("ELEVATED_TEMPERATURE")
            if state.margins.pressureMarginKpa < 0:
                pressure = 5.0
                rules.append("RULE_PRESSURE_LOW")
                reasons.append("LOW_OIL_PRESSURE_WARNING")
            if state.margins.vibrationMarginMmS < 4:
                vibration = 10.0
                rules.append("RULE_VIBRATION_EXCEEDED")
                reasons.append("HIGH_ENGINE_VIBRATION")
        total = temp + pressure + vibration + quality
        if total == 100:
            reasons.append("ALL_SYSTEMS_NOMINAL")
        return HealthSnapshot(
            engineId=state.engineId, missionId=state.missionId,
            correlationId=state.correlationId, snapshotTime=state.stateTime,
            producerVersion="m3-health@1.1.0", healthScore=total,
            trend="DEGRADING" if rules else "STABLE",
            subScores=SubScores(temperature=temp, pressure=pressure, vibration=vibration),
            violatedRules=rules, reasonCodes=reasons,
            ruleVersion="sih-margin-rules@1.1.0", dataQualityIssue=data_issue,
        )

app = FastAPI(title="AeroTwin M3 Health Monitor", version="1.1.0")
engine = PhysicsHealthEngine()

@app.post("/evaluate", response_model=HealthSnapshot, response_model_exclude_none=True)
def evaluate_engine_health(twin_state: TwinStateInput):
    return engine.evaluate_health(twin_state)

@app.get("/health")
def health_check():
    return {"status": "healthy", "producerVersion": "m3-health@1.1.0"}

import pytest
from main import PhysicsHealthEngine, TwinStateInput

def test_nominal_health_score():
    engine = PhysicsHealthEngine()
    state = TwinStateInput(
        engineId="ENG-01",
        missionId="MISS-01",
        stateTime="2026-08-25T10:00:00Z",
        load=75.0,
        derivedFeatures={"rpm": 4500.0, "vibration_rms": 0.02},
        margins={"temperature_margin_c": 70.0, "pressure_margin_bar": 1.5},
        stateQuality="VALID"
    )
    result = engine.evaluate_health(state)
    assert result.healthScore == 100.0
    assert "ALL_SYSTEMS_NOMINAL" in result.reasonCodes

def test_overheating_fault_detection():
    engine = PhysicsHealthEngine()
    state = TwinStateInput(
        engineId="ENG-01",
        missionId="MISS-01",
        stateTime="2026-08-25T10:05:00Z",
        load=95.0,
        derivedFeatures={"rpm": 5800.0, "vibration_rms": 0.03},
        margins={"temperature_margin_c": 10.0, "pressure_margin_bar": 1.5}, # High temp
        stateQuality="VALID"
    )
    result = engine.evaluate_health(state)
    assert result.healthScore < 100.0
    assert "RULE_TEMP_CRITICAL" in result.violatedRules
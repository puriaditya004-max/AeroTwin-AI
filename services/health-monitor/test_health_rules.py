import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from main import app, PhysicsHealthEngine, TwinStateInput

def sample():
    return json.loads((Path(__file__).resolve().parents[2] / "packages/schemas/samples/TwinState.sample.json").read_text())

def test_canonical_m2_good_state_is_accepted():
    state = sample()
    state["margins"] = {"tempMarginC": 45, "pressureMarginKpa": 100, "vibrationMarginMmS": 9}
    response = TestClient(app).post("/evaluate", json=state)
    assert response.status_code == 200
    result = response.json()
    assert result["healthScore"] == 100
    assert result["correlationId"] == state["correlationId"]
    assert result["producerVersion"] and result["snapshotTime"] and result["trend"]

@pytest.mark.parametrize("margin,value,rule", [("tempMarginC", -5, "RULE_TEMP_CRITICAL"),
    ("pressureMarginKpa", -50, "RULE_PRESSURE_LOW"), ("vibrationMarginMmS", -1, "RULE_VIBRATION_EXCEEDED")])
def test_canonical_margins_trigger_rules(margin,value,rule):
    state = sample()
    state["margins"][margin] = value
    result = PhysicsHealthEngine().evaluate_health(TwinStateInput.model_validate(state))
    assert rule in result.violatedRules
    assert result.healthScore < 100

@pytest.mark.parametrize("quality", ["DEGRADED", "STALE"])
def test_bad_quality_does_not_claim_engine_failure(quality):
    state = sample()
    state["stateQuality"] = quality
    state["margins"]["tempMarginC"] = -100
    result = PhysicsHealthEngine().evaluate_health(TwinStateInput.model_validate(state))
    assert result.dataQualityIssue
    assert result.violatedRules == []
    assert "SENSOR_DATA_DEGRADED" in result.reasonCodes

def test_missing_correlation_is_rejected():
    state = sample()
    del state["correlationId"]
    assert TestClient(app).post("/evaluate", json=state).status_code == 422

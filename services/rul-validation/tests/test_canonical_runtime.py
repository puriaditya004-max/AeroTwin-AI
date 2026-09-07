import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from app import main
from app.predictor import RULPredictor


def payload():
    root = Path(__file__).resolve().parents[3]
    state = json.loads((root / "packages/schemas/samples/TwinState.sample.json").read_text())
    health = json.loads((root / "packages/schemas/samples/HealthSnapshot.sample.json").read_text())
    for key in ("engineId", "missionId", "correlationId"): health[key] = state[key]
    health["snapshotTime"] = state["stateTime"]
    state["sensors"] = {"oilTempC":92, "oilPressureKpa":430, "vibrationMmS":3.2, "rpm":2400}
    return {"state":state, "health":health}


def test_canonical_runtime_is_repeatable_and_labels_proxy():
    client = TestClient(main.app)
    first = client.post("/estimate",json=payload())
    second = client.post("/estimate",json=payload())
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["basis"] == "RULE_BASED_PROXY"
    assert first.json()["experimental"]
    assert first.json()["lowerBound"] <= first.json()["cycles"] <= first.json()["upperBound"]


def test_mismatched_upstream_events_are_rejected():
    data=payload();data["health"]["correlationId"]="wrong-event"
    assert TestClient(main.app).post("/estimate",json=data).status_code == 422


def test_no_invented_sensor_defaults():
    data=payload();del data["state"]["sensors"]
    assert TestClient(main.app).post("/estimate",json=data).status_code == 422


def test_readiness_fails_without_usable_model(monkeypatch):
    monkeypatch.setattr(main,"predictor",None)
    monkeypatch.setattr(main,"model_load_error","missing model",raising=False)
    assert TestClient(main.app).get("/health").status_code == 503


def test_experimental_fallback_requires_opt_in(monkeypatch,tmp_path):
    monkeypatch.setenv("M5_ALLOW_EXPERIMENTAL_FALLBACK","false")
    monkeypatch.setenv("M5_ENABLE_MLFLOW","false")
    monkeypatch.setattr("app.predictor.MODEL_FILE",tmp_path / "missing")
    with pytest.raises(RuntimeError): RULPredictor()

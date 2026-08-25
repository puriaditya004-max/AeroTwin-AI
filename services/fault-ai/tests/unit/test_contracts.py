"""
Unit tests for Gate 01 - Contracts and FastAPI Skeleton
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.contracts import TwinState, Margins, DerivedFeatures, StateQuality, FaultPrediction, FaultType


@pytest.fixture
def client():
    return TestClient(app)


def test_health_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert data["service"] == "m4-fault-ai"


def test_health_ready(client):
    response = client.get("/health/ready")
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "READY"
    else:
        detail = response.json()["detail"]
        assert detail["message"] == "Models or feature pipeline not loaded"
        assert "missingArtifacts" in detail


def test_twin_state_contract_validation():
    state = TwinState(
        engineId="ENG-001",
        missionId="MIS-101",
        correlationId="CORR-001",
        stateTime=datetime.now(timezone.utc),
        producerVersion="1.0.0",
        load=75.5,
        margins=Margins(tempMarginC=12.0, pressureMarginKpa=50.0, vibrationMarginMmS=2.0),
        derivedFeatures=DerivedFeatures(
            rollingMeanRpm=2400.0,
            rollingStdVibration=0.1,
            rateOfChangeOilTempCPerMin=0.05,
            sampleWindowSeconds=30.0
        ),
        stateQuality=StateQuality.GOOD,
        syncLagMs=45.0
    )
    assert state.engineId == "ENG-001"
    assert state.stateQuality == StateQuality.GOOD


def test_predict_endpoint_safety_rule(client):
    stale_payload = {
        "engineId": "ENG-001",
        "missionId": "MIS-101",
        "correlationId": "CORR-001",
        "stateTime": datetime.now(timezone.utc).isoformat(),
        "producerVersion": "1.0.0",
        "load": 75.5,
        "margins": {"tempMarginC": -5.0, "pressureMarginKpa": -20.0, "vibrationMarginMmS": 15.0},
        "derivedFeatures": {
            "rollingMeanRpm": 2400.0,
            "rollingStdVibration": 5.0,
            "rateOfChangeOilTempCPerMin": 8.0,
            "sampleWindowSeconds": 30.0
        },
        "stateQuality": "STALE",
        "syncLagMs": 1500.0
    }
    response = client.post("/predict", json=stale_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["faultType"] == "NONE"
    assert data["confidence"] == 0.0
    assert data["anomalyScore"] == 0.0

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app, checkpoint, processor


def test_liveness_endpoint_returns_metrics():
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "UP"
    assert "metrics" in response.json()["details"]


def test_latest_state_endpoint_returns_checkpointed_state():
    client = TestClient(app)
    payload = {
        "engineId": "ENG-API",
        "missionId": "MIS-API",
        "correlationId": "corr-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "producerVersion": "m1-test",
        "qualityFlag": "OK",
        "sensors": {
            "rpm": 2200,
            "oilPressureKpa": 410,
            "oilTempC": 90,
            "coolantTempC": 93,
            "vibrationMmS": 2.8,
            "fuelFlowLph": 32,
            "throttlePct": 58,
            "altitudeM": 900,
            "ambientTempC": 21,
            "ambientPressureKpa": 90,
        },
    }
    state = processor.process_payload(payload).state
    checkpoint.save(state)

    response = client.get("/state/ENG-API/MIS-API")

    assert response.status_code == 200
    assert response.json()["correlationId"] == "corr-api"

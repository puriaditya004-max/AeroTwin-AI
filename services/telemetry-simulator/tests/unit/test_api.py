from fastapi.testclient import TestClient
import pytest

from app.main import app, runner


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
        if runner.state.status == "running":
            import asyncio

            try:
                asyncio.get_event_loop().run_until_complete(runner.stop())
            except RuntimeError:
                pass


def test_list_and_start_stop_scenarios(client):
    client = TestClient(app)

    listed = client.get("/scenarios")
    assert listed.status_code == 200
    names = {item["id"] for item in listed.json()["scenarios"]}
    assert names == {
        "normal",
        "overheating",
        "oil_pressure_degradation",
        "vibration_misfire",
        "sensor_dropout",
    }

    started = client.post("/scenarios/oil_pressure_degradation/start", json={"seed": 7})
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "running"
    assert body["scenario"] == "oil_pressure_degradation"
    assert body["correlationId"]
    assert body["seed"] == 7

    conflict = client.post("/scenarios/normal/start")
    assert conflict.status_code == 409

    stopped = client.post("/scenarios/oil_pressure_degradation/stop")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"

    missing = client.post("/scenarios/does-not-exist/start")
    assert missing.status_code == 404


def test_health_live_and_ready(client):
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "UP"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "READY"


def test_metrics_endpoint_exposes_publisher_snapshot(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "framesSent" in payload
    assert "dropRate" in payload
    assert "currentScenario" in payload

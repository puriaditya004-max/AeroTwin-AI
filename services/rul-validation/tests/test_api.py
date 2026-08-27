from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["model_loaded"] is True


def test_predict_rul_endpoint():
    payload = {
        "temperature": 75,
        "vibration": 1.2,
        "pressure": 92,
        "rpm": 2850,
        "load": 75,
        "health_index": 0.7,
    }

    response = client.post(
        "/predict-rul",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert "predicted_rul" in data
    assert "unit" in data

    assert isinstance(
        data["predicted_rul"],
        float,
    )

    assert data["predicted_rul"] >= 0
    assert data["unit"] == "cycles"


def test_invalid_health_index():
    payload = {
        "temperature": 75,
        "vibration": 1.2,
        "pressure": 92,
        "rpm": 2850,
        "load": 75,
        "health_index": 1.5,
    }

    response = client.post(
        "/predict-rul",
        json=payload,
    )

    assert response.status_code == 422
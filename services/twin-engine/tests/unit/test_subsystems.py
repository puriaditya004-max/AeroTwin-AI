from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app, checkpoint, processor
from app.processor import TwinProcessor
from app.settings import get_settings
from state.contract_view import build_m2_contract


def frame(**sensor_overrides):
    sensors = {
        "rpm": 2400,
        "oilPressureKpa": 430,
        "oilTempC": 92,
        "coolantTempC": 96,
        "vibrationMmS": 3.2,
        "fuelFlowLph": 35,
        "throttlePct": 62,
        "altitudeM": 1200,
        "ambientTempC": 22,
        "ambientPressureKpa": 88,
    }
    sensors.update(sensor_overrides)
    return {
        "engineId": "ENGINE-1",
        "missionId": "MIS-SUB",
        "correlationId": "corr-sub",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "producerVersion": "m1-test",
        "qualityFlag": "OK",
        "sensors": sensors,
    }


def twin_state(**sensor_overrides):
    result = TwinProcessor(get_settings()).process_payload(frame(**sensor_overrides))
    assert result.state is not None
    return result.state


def test_nominal_frame_is_all_nominal():
    sub = twin_state().subsystemState

    assert sub.thermalState == "normal"
    assert sub.lubricationState == "healthy"
    assert sub.combustionState == "stable"
    assert sub.vibrationState == "normal"
    assert sub.overallState == "nominal"
    assert sub.basis == "context-baseline"


def test_hot_oil_above_context_baseline_is_elevated_and_degraded_overall():
    sub = twin_state(oilTempC=125, coolantTempC=100).subsystemState

    assert sub.thermalState == "elevated"
    assert sub.overallState == "degraded"
    assert "THERMAL_ABOVE_CONTEXT_BASELINE" in sub.reasons


def test_oil_temperature_at_profile_critical_limit_is_critical():
    sub = twin_state(oilTempC=132).subsystemState

    assert sub.thermalState == "critical"
    assert sub.overallState == "critical"


def test_hot_ambient_does_not_flag_normal_oil_temperature():
    # Same oil temperature that would look high on a cool day is normal at 40 C ambient.
    sub = twin_state(oilTempC=108, coolantTempC=110, ambientTempC=40).subsystemState

    assert sub.thermalState == "normal"


def test_low_oil_pressure_is_degraded_then_critical():
    degraded = twin_state(oilPressureKpa=370).subsystemState
    critical = twin_state(oilPressureKpa=200).subsystemState

    assert degraded.lubricationState == "degraded"
    assert degraded.overallState == "degraded"
    assert critical.lubricationState == "critical"
    assert critical.overallState == "critical"


def test_vibration_bands_elevated_and_severe():
    elevated = twin_state(vibrationMmS=6.0).subsystemState
    severe = twin_state(vibrationMmS=12.5).subsystemState

    assert elevated.vibrationState == "elevated"
    assert severe.vibrationState == "severe"
    assert severe.overallState == "critical"


def test_cylinder_spread_marks_combustion_unstable():
    sub = twin_state(chtCylindersC=[180, 185, 182, 225]).subsystemState

    assert sub.combustionState == "unstable"
    assert sub.overallState == "degraded"
    assert "CHT_CYLINDER_SPREAD_HIGH" in sub.reasons


def test_contract_view_matches_m2_contract_shape():
    state = twin_state(oilTempC=125, oilPressureKpa=330)
    contract = build_m2_contract(state).model_dump()

    assert set(contract) == {"aircraftId", "engineId", "state", "estimatedValues", "deviation"}
    assert contract["aircraftId"] == "UAV-001"
    assert contract["engineId"] == "ENGINE-1"
    assert set(contract["state"]) == {
        "engineSpeed", "thermalState", "lubricationState",
        "combustionState", "vibrationState", "overallState",
    }
    assert set(contract["estimatedValues"]) == {
        "expectedOilTemperature", "expectedOilPressure", "expectedVibration",
    }
    assert set(contract["deviation"]) == {"oilTemperature", "oilPressure", "vibration"}
    assert contract["state"]["engineSpeed"] == 2400
    assert contract["deviation"]["oilTemperature"] > 8
    assert contract["deviation"]["oilPressure"] < -25
    derived = state.derivedFeatures
    assert contract["estimatedValues"]["expectedOilTemperature"] == round(derived.expectedOilTempC, 3)


def test_frame_aircraft_id_overrides_default():
    payload = frame()
    payload["aircraftId"] = "UAV-007"
    state = TwinProcessor(get_settings()).process_payload(payload).state

    assert build_m2_contract(state).aircraftId == "UAV-007"


def test_contract_endpoint_returns_contract(monkeypatch):
    monkeypatch.setenv("M2_CHECKPOINT_BACKEND", "memory")
    state = processor.process_payload(frame(oilTempC=125)).state
    checkpoint.save(state)
    client = TestClient(app)

    response = client.get("/contract/ENGINE-1")

    assert response.status_code == 200
    body = response.json()
    assert body["state"]["thermalState"] == "elevated"
    assert body["engineId"] == "ENGINE-1"

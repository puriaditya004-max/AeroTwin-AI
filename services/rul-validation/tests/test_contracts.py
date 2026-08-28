import pytest
from pydantic import ValidationError

from app.schemas import M3M4HealthData


def test_valid_m3_m4_contract():
    data = M3M4HealthData(
        engine_id="ENG-001",
        mission_id="MISSION-001",
        correlation_id="CORR-001",
        cycle=120,
        temperature=80.0,
        vibration=2.5,
        pressure=1.2,
        rpm=3000,
        load=75.0,
        health_index=0.8,
    )

    assert data.engine_id == "ENG-001"
    assert data.cycle == 120
    assert data.health_index == 0.8


def test_health_index_cannot_exceed_one():
    with pytest.raises(ValidationError):
        M3M4HealthData(
            engine_id="ENG-001",
            mission_id="MISSION-001",
            correlation_id="CORR-001",
            cycle=120,
            temperature=80.0,
            vibration=2.5,
            pressure=1.2,
            rpm=3000,
            load=75.0,
            health_index=1.5,
        )


def test_health_index_cannot_be_negative():
    with pytest.raises(ValidationError):
        M3M4HealthData(
            engine_id="ENG-001",
            mission_id="MISSION-001",
            correlation_id="CORR-001",
            cycle=120,
            temperature=80.0,
            vibration=2.5,
            pressure=1.2,
            rpm=3000,
            load=75.0,
            health_index=-0.1,
        )


def test_cycle_cannot_be_negative():
    with pytest.raises(ValidationError):
        M3M4HealthData(
            engine_id="ENG-001",
            mission_id="MISSION-001",
            correlation_id="CORR-001",
            cycle=-1,
            temperature=80.0,
            vibration=2.5,
            pressure=1.2,
            rpm=3000,
            load=75.0,
            health_index=0.8,
        )


def test_empty_engine_id_is_rejected():
    with pytest.raises(ValidationError):
        M3M4HealthData(
            engine_id="",
            mission_id="MISSION-001",
            correlation_id="CORR-001",
            cycle=120,
            temperature=80.0,
            vibration=2.5,
            pressure=1.2,
            rpm=3000,
            load=75.0,
            health_index=0.8,
        )
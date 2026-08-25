from datetime import datetime, timedelta, timezone

from app.contracts import QualityFlag, StateQuality
from app.processor import TwinProcessor
from app.settings import get_settings


def sample_frame(**overrides):
    now = datetime.now(timezone.utc)
    frame = {
        "engineId": "ENG-001",
        "missionId": "MIS-001",
        "correlationId": "corr-001",
        "timestamp": now.isoformat(),
        "producerVersion": "m1-test",
        "qualityFlag": "OK",
        "sensors": {
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
        },
    }
    frame.update(overrides)
    return frame


def processor():
    return TwinProcessor(get_settings())


def test_valid_telemetry_to_twin_state_preserves_contract_fields():
    result = processor().process_payload(sample_frame())

    assert result.accepted is True
    assert result.state is not None
    assert result.state.engineId == "ENG-001"
    assert result.state.missionId == "MIS-001"
    assert result.state.correlationId == "corr-001"
    assert 0 <= result.state.load <= 100
    assert result.state.derivedFeatures.sampleWindowSeconds == 30
    assert processor().metrics_snapshot()["averageSyncLagMs"] is None


def test_duplicate_frame_is_idempotent_and_does_not_publish_state_twice():
    engine = processor()
    frame = sample_frame()

    first = engine.process_payload(frame)
    duplicate = engine.process_payload(frame)

    assert first.state is not None
    assert duplicate.state is None
    assert duplicate.reason == "duplicate"
    assert engine.metrics["framesDeduped"] == 1


def test_bad_quality_flag_degrades_state_quality():
    result = processor().process_payload(sample_frame(qualityFlag=QualityFlag.DROPOUT.value))

    assert result.state is not None
    assert result.state.stateQuality == StateQuality.DEGRADED


def test_stale_frame_maps_to_stale_state_quality():
    old_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    result = processor().process_payload(sample_frame(timestamp=old_time.isoformat()))

    assert result.state is not None
    assert result.state.stateQuality == StateQuality.STALE


def test_out_of_order_beyond_tolerance_is_rejected():
    engine = processor()
    now = datetime.now(timezone.utc)
    first = sample_frame(timestamp=now.isoformat(), correlationId="corr-new")
    old = sample_frame(timestamp=(now - timedelta(seconds=10)).isoformat(), correlationId="corr-old")

    assert engine.process_payload(first).accepted is True
    result = engine.process_payload(old)

    assert result.accepted is False
    assert result.reason == "late"
    assert engine.metrics["lateFrames"] == 1


def test_per_mission_windows_are_isolated():
    engine = processor()
    mission_a = sample_frame(missionId="MIS-A", correlationId="corr-a")
    mission_b = sample_frame(missionId="MIS-B", correlationId="corr-b")

    engine.process_payload(mission_a)
    engine.process_payload(mission_b)

    assert len(engine.windows.latest("ENG-001", "MIS-A")) == 1
    assert len(engine.windows.latest("ENG-001", "MIS-B")) == 1


def test_metrics_snapshot_reports_sync_lag_distribution():
    engine = processor()
    engine.process_payload(sample_frame(correlationId="corr-1"))
    engine.process_payload(sample_frame(correlationId="corr-2"))

    metrics = engine.metrics_snapshot()

    assert metrics["lastSyncLagMs"] is not None
    assert metrics["averageSyncLagMs"] is not None
    assert metrics["p95SyncLagMs"] is not None

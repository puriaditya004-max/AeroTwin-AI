from datetime import datetime, timezone

from app.contracts import QualityFlag, Sensors, TelemetryFrame
from app.settings import QualityRates
from simulation.noise import apply_quality_decision, decide_quality_event
from simulation.seed import rng_from_seed


def _frame() -> TelemetryFrame:
    return TelemetryFrame(
        schemaVersion="2.0.0",
        engineId="ENG-001",
        missionId="MSN-TEST-1",
        frameId="frame-000001",
        correlationId="corr-test-1",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        producerVersion="1.0.0",
        sensors=Sensors(
            rpm=2400,
            oilPressureKpa=220,
            oilTempC=92,
            coolantTempC=88,
            vibrationMmS=3.2,
            fuelFlowLph=18.5,
            throttlePct=65,
            altitudeM=3200,
            ambientTempC=12,
            ambientPressureKpa=68,
        ),
        qualityFlag=QualityFlag.OK,
        scenarioId="sensor_dropout",
    )


def test_dropout_sets_quality_flag_and_can_skip_publish():
    rng = rng_from_seed(1)
    decision = decide_quality_event(rng, QualityRates(dropoutRate=1.0))
    frames = apply_quality_decision(_frame(), decision)
    assert decision.skip_publish is True
    assert len(frames) == 1
    assert frames[0].qualityFlag == QualityFlag.DROPOUT


def test_dropout_flag_rate_publishes_dropout_marker():
    rng = rng_from_seed(2)
    decision = decide_quality_event(rng, QualityRates(dropoutFlagRate=1.0))
    frames = apply_quality_decision(_frame(), decision)
    assert decision.skip_publish is False
    assert frames[0].qualityFlag == QualityFlag.DROPOUT


def test_duplicate_sets_quality_flag_on_second_frame():
    rng = rng_from_seed(3)
    decision = decide_quality_event(rng, QualityRates(duplicateRate=1.0))
    frames = apply_quality_decision(_frame(), decision)
    assert [frame.qualityFlag for frame in frames] == [QualityFlag.OK, QualityFlag.DUPLICATE]
    assert frames[0].timestamp == frames[1].timestamp
    assert frames[0].sensors.rpm == frames[1].sensors.rpm


def test_out_of_order_sets_quality_flag_and_shifts_timestamp():
    rng = rng_from_seed(4)
    rates = QualityRates(outOfOrderRate=1.0, outOfOrderShiftMs=2000)
    decision = decide_quality_event(rng, rates)
    original = _frame()
    frames = apply_quality_decision(original, decision)
    assert len(frames) == 1
    assert frames[0].qualityFlag == QualityFlag.OUT_OF_ORDER
    delta_ms = (original.timestamp - frames[0].timestamp).total_seconds() * 1000
    assert delta_ms == 2000

import asyncio

import pytest

from app.contracts import QualityFlag, Sensors, TelemetryFrame
from app.settings import PublishSettings
from datetime import datetime, timezone
from stream.publisher import RedisPublisher, RetryingPublisher


def _frame() -> TelemetryFrame:
    return TelemetryFrame(
        schemaVersion="2.0.0",
        engineId="ENG-001",
        missionId="MSN-TEST-1",
        frameId="frame-000001",
        correlationId="corr-pub-1",
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
        scenarioId="normal",
    )


class FlakyRedis:
    def __init__(self, failures: int):
        self.failures = failures
        self.calls = []
        self.sleeps = []

    async def xadd(self, stream_name, fields):
        self.calls.append((stream_name, fields))
        if len(self.calls) <= self.failures:
            raise ConnectionError("redis unavailable")
        return b"1-0"


@pytest.mark.asyncio
async def test_publisher_retries_then_succeeds(monkeypatch):
    redis = FlakyRedis(failures=2)
    inner = RedisPublisher(redis, "telemetry.frame.v1")
    settings = PublishSettings(
        defaultRateHz=1,
        replayEpoch="2026-01-01T00:00:00Z",
        maxRetryAttempts=4,
        initialBackoffMs=1,
        maxBackoffMs=4,
        backoffMultiplier=2,
        leaseTtlSeconds=5,
    )
    publisher = RetryingPublisher(inner, settings)
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    message_id = await publisher.publish(_frame())
    assert message_id == "1-0"
    assert len(redis.calls) == 3
    assert publisher.retry_count == 2
    assert publisher.frames_sent == 1
    assert sleeps == [0.001, 0.002]


@pytest.mark.asyncio
async def test_publisher_gives_up_after_bounded_retries(monkeypatch):
    redis = FlakyRedis(failures=10)
    inner = RedisPublisher(redis, "telemetry.frame.v1")
    settings = PublishSettings(
        defaultRateHz=1,
        replayEpoch="2026-01-01T00:00:00Z",
        maxRetryAttempts=3,
        initialBackoffMs=1,
        maxBackoffMs=4,
        backoffMultiplier=2,
        leaseTtlSeconds=5,
    )
    publisher = RetryingPublisher(inner, settings)

    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    with pytest.raises(ConnectionError):
        await publisher.publish(_frame())
    assert publisher.publish_failures == 1
    assert publisher.frames_sent == 0
    assert len(redis.calls) == 3

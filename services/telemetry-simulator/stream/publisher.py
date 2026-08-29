from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from typing import Any, Protocol

from app.contracts import TelemetryFrame
from app.logging import log_event
from app.settings import PublishSettings


class FramePublisher(Protocol):
    async def publish(self, frame: TelemetryFrame) -> str: ...

    async def ping(self) -> bool: ...


class InMemoryPublisher:
    def __init__(self) -> None:
        self.published: list[TelemetryFrame] = []
        self.stream_ids: list[str] = []

    async def ping(self) -> bool:
        return True

    async def publish(self, frame: TelemetryFrame) -> str:
        self.published.append(frame)
        message_id = f"{len(self.published)}-0"
        self.stream_ids.append(message_id)
        return message_id


class RedisPublisher:
    def __init__(self, redis_client: Any, stream_name: str, payload_field: str = "payload"):
        self.redis_client = redis_client
        self.stream_name = stream_name
        self.payload_field = payload_field

    async def ping(self) -> bool:
        return bool(await self.redis_client.ping())

    async def publish(self, frame: TelemetryFrame) -> str:
        payload = frame.model_dump(mode="json")
        message_id = await self.redis_client.xadd(
            self.stream_name,
            {
                self.payload_field: json.dumps(payload),
                "correlationId": frame.correlationId,
                "qualityFlag": frame.qualityFlag.value,
                "scenarioId": frame.scenarioId or "",
            },
        )
        if isinstance(message_id, bytes):
            return message_id.decode("utf-8")
        return str(message_id)


class RetryingPublisher:
    def __init__(self, inner: FramePublisher, settings: PublishSettings):
        self.inner = inner
        self.settings = settings
        self.frames_sent = 0
        self.frames_dropped = 0
        self.publish_failures = 0
        self.retry_count = 0
        self.current_scenario: str | None = None
        self.last_error: str | None = None
        self.last_published_at: datetime | None = None
        self._quality_counts = {"OK": 0, "DEGRADED": 0, "DROPOUT": 0, "DUPLICATE": 0, "OUT_OF_ORDER": 0}

    def metrics_snapshot(self) -> dict[str, Any]:
        sent = self.frames_sent
        dropped = self.frames_dropped
        attempted = sent + dropped
        return {
            "framesSent": sent,
            "framesDropped": dropped,
            "dropRate": (dropped / attempted) if attempted else 0.0,
            "publishFailures": self.publish_failures,
            "retryCount": self.retry_count,
            "currentScenario": self.current_scenario,
            "lastError": self.last_error,
            "lastPublishedAt": self.last_published_at.isoformat() if self.last_published_at else None,
            "qualityCounts": dict(self._quality_counts),
        }

    def record_drop(self) -> None:
        self.frames_dropped += 1
        self._quality_counts["DROPOUT"] += 1

    async def ping(self) -> bool:
        return await self.inner.ping()

    async def publish(self, frame: TelemetryFrame) -> str:
        delay_s = self.settings.initialBackoffMs / 1000.0
        max_delay_s = self.settings.maxBackoffMs / 1000.0
        last_error: Exception | None = None
        for attempt in range(1, self.settings.maxRetryAttempts + 1):
            try:
                message_id = await self.inner.publish(frame)
                self.frames_sent += 1
                self.last_error = None
                self.last_published_at = datetime.now(timezone.utc)
                self._quality_counts[frame.qualityFlag.value] = self._quality_counts.get(frame.qualityFlag.value, 0) + 1
                log_event(
                    "frame_published",
                    correlationId=frame.correlationId,
                    scenario=frame.scenarioId,
                    qualityFlag=frame.qualityFlag.value,
                    missionId=frame.missionId,
                    engineId=frame.engineId,
                    frameId=frame.frameId,
                    stream=getattr(self.inner, "stream_name", None),
                    messageId=message_id,
                    attempt=attempt,
                )
                return message_id
            except Exception as exc:
                last_error = exc
                self.retry_count += 1
                self.last_error = str(exc)
                log_event(
                    "frame_publish_retry",
                    correlationId=frame.correlationId,
                    scenario=frame.scenarioId,
                    qualityFlag=frame.qualityFlag.value,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt >= self.settings.maxRetryAttempts:
                    break
                await asyncio.sleep(delay_s)
                delay_s = min(delay_s * self.settings.backoffMultiplier, max_delay_s)
        self.publish_failures += 1
        log_event(
            "frame_publish_failed",
            correlationId=frame.correlationId,
            scenario=frame.scenarioId,
            qualityFlag=frame.qualityFlag.value,
            error=str(last_error),
        )
        raise last_error if last_error is not None else RuntimeError("publish failed")

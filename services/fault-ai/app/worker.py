"""
Gate 07: Production Redis Stream Consumer and M6 Publisher Worker

Consumes stream twin.state.v1 using consumer group m4-fault-ai via XREADGROUP.
Maintains 30-second rolling window per (engineId, missionId) tuple.
Sends frames to M4 predict endpoint, publishes FaultPrediction events to M6 with bounded retry and idempotency,
and acknowledges (XACK) Redis messages only upon successful handoff.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx

try:
    import redis.asyncio as redis_async
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

from app.contracts import TwinState, FaultPrediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("m4-worker")


@dataclass
class WorkerMetrics:
    frames_received: int = 0
    predictions_succeeded: int = 0
    predictions_failed: int = 0
    m6_publish_succeeded: int = 0
    m6_publish_failed: int = 0
    redis_messages_acked: int = 0
    redis_messages_dlq: int = 0
    redis_pending_claimed: int = 0
    last_error: Optional[str] = None
    last_prediction_at: Optional[str] = None


class M4Worker:
    """Production Redis Stream consumer and M6 publisher with bounded retries."""

    def __init__(
        self,
        m6_ingest_url: str = "http://localhost:8006/ingest/fault",
        m4_predict_url: str = "http://localhost:8004/predict",
        redis_url: str = "redis://localhost:6379/0",
        stream_name: str = "twin.state.v1",
        group_name: str = "m4-fault-ai",
        consumer_name: str = "m4-worker-1",
        max_retries: int = 3,
        dead_letter_stream: str = "fault.prediction.dlq.v1",
        pending_idle_ms: int = 30000,
        dead_letter_after_deliveries: int = 5
    ):
        self.m6_ingest_url = os.getenv("M6_INGEST_URL", m6_ingest_url)
        self.m4_predict_url = os.getenv("M4_PREDICT_URL", m4_predict_url)
        self.redis_url = os.getenv("REDIS_URL", redis_url)
        self.stream_name = os.getenv("M4_INPUT_STREAM", stream_name)
        self.group_name = os.getenv("M4_CONSUMER_GROUP", group_name)
        self.consumer_name = os.getenv("M4_CONSUMER_NAME", consumer_name)
        self.dead_letter_stream = os.getenv("M4_DEAD_LETTER_STREAM", dead_letter_stream)
        self.max_retries = int(os.getenv("M4_MAX_RETRIES", str(max_retries)))
        self.pending_idle_ms = int(os.getenv("M4_PENDING_IDLE_MS", str(pending_idle_ms)))
        self.dead_letter_after_deliveries = int(
            os.getenv("M4_DEAD_LETTER_AFTER_DELIVERIES", str(dead_letter_after_deliveries))
        )
        self.client = httpx.AsyncClient(timeout=5.0)
        self.metrics = WorkerMetrics()

        # Keyed by (engineId, missionId) tuple
        self.rolling_windows: Dict[Tuple[str, str], List[dict]] = {}

    def snapshot_metrics(self) -> Dict[str, Any]:
        """Returns serializable worker metrics for tests and operator diagnostics."""
        return asdict(self.metrics)

    def update_rolling_window(self, engine_id: str, mission_id: str, state_dict: dict) -> List[dict]:
        """Maintains maximum 30 rolling state frames per (engineId, missionId)."""
        key = (engine_id, mission_id)
        if key not in self.rolling_windows:
            self.rolling_windows[key] = []

        window = self.rolling_windows[key]
        window.append(state_dict)
        if len(window) > 30:
            window.pop(0)

        return window

    async def publish_to_m6_with_retry(self, prediction_payload: dict) -> bool:
        """Publishes FaultPrediction to M6 with bounded exponential backoff and idempotency header."""
        correlation_id = prediction_payload.get("correlationId", "UNKNOWN")
        headers = {
            "Content-Type": "application/json",
            "X-Idempotency-Key": correlation_id
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self.client.post(
                    self.m6_ingest_url,
                    json=prediction_payload,
                    headers=headers
                )
                if resp.status_code in (200, 201, 202):
                    logger.info(
                        f"Published prediction to M6 [Correlation: {correlation_id}] "
                        f"(Status: {resp.status_code}, FaultType: {prediction_payload.get('faultType')})"
                    )
                    return True
                else:
                    logger.warning(f"M6 non-success status {resp.status_code} (Attempt {attempt}/{self.max_retries})")
            except Exception as e:
                logger.warning(f"M6 connection error: {e} (Attempt {attempt}/{self.max_retries})")

            if attempt < self.max_retries:
                backoff_sec = 0.5 * (2 ** (attempt - 1))
                await asyncio.sleep(backoff_sec)

        logger.error(f"Failed to publish prediction to M6 after {self.max_retries} attempts [Correlation: {correlation_id}]")
        self.metrics.m6_publish_failed += 1
        return False

    async def process_twin_state(self, twin_state_dict: dict) -> Optional[dict]:
        """Processes twin state through M4 predict API and pushes to M6."""
        self.metrics.frames_received += 1
        engine_id = twin_state_dict.get("engineId", "ENG-DEFAULT")
        mission_id = twin_state_dict.get("missionId", "MIS-DEFAULT")
        window = self.update_rolling_window(engine_id, mission_id, twin_state_dict)

        payload = {
            "engineId": engine_id,
            "missionId": mission_id,
            "states": window
        }

        try:
            resp = await self.client.post(self.m4_predict_url, json=payload)
            if resp.status_code != 200:
                logger.error(f"Predict API failed with status {resp.status_code}: {resp.text}")
                self.metrics.predictions_failed += 1
                self.metrics.last_error = f"predict_status_{resp.status_code}"
                return None

            prediction_data = resp.json()
            self.metrics.predictions_succeeded += 1
            success = await self.publish_to_m6_with_retry(prediction_data)
            if success:
                self.metrics.m6_publish_succeeded += 1
                self.metrics.last_prediction_at = datetime.now(timezone.utc).isoformat()
            return prediction_data if success else None

        except Exception as e:
            logger.error(f"Worker pipeline error processing frame: {e}")
            self.metrics.predictions_failed += 1
            self.metrics.last_error = str(e)
            return None

    def decode_stream_payload(self, message_data: Dict[Any, Any]) -> Optional[dict]:
        """Extracts and decodes the JSON payload field from a Redis stream message."""
        raw_payload = message_data.get(b"payload") or message_data.get("payload")
        if raw_payload is None:
            return None
        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode("utf-8")
        return json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload

    async def send_to_dead_letter(
        self,
        redis_client: Any,
        message_id: Any,
        state_dict: dict,
        reason: str
    ) -> None:
        """Persists poison messages so they can be replayed without blocking the consumer group."""
        payload = {
            "sourceStream": self.stream_name,
            "sourceMessageId": str(message_id),
            "reason": reason,
            "failedAt": datetime.now(timezone.utc).isoformat(),
            "payload": json.dumps(state_dict),
        }
        await redis_client.xadd(self.dead_letter_stream, payload)
        await redis_client.xack(self.stream_name, self.group_name, message_id)
        self.metrics.redis_messages_dlq += 1
        self.metrics.redis_messages_acked += 1

    async def handle_redis_message(self, redis_client: Any, message_id: Any, message_data: Dict[Any, Any]) -> None:
        """Processes a single Redis stream message with ack-after-success semantics."""
        try:
            state_dict = self.decode_stream_payload(message_data)
            if state_dict is None:
                await self.send_to_dead_letter(redis_client, message_id, {}, "missing_payload")
                return

            prediction = await self.process_twin_state(state_dict)
            if prediction is not None:
                await redis_client.xack(self.stream_name, self.group_name, message_id)
                self.metrics.redis_messages_acked += 1
        except json.JSONDecodeError as exc:
            self.metrics.last_error = f"invalid_json:{exc}"
            await self.send_to_dead_letter(redis_client, message_id, {}, "invalid_json")
        except Exception as exc:
            self.metrics.last_error = str(exc)
            logger.error(f"Redis message processing failed for {message_id}: {exc}")

    async def recover_pending_messages(self, redis_client: Any) -> None:
        """Claims idle pending messages and moves poison messages to DLQ after bounded deliveries."""
        try:
            result = await redis_client.xautoclaim(
                self.stream_name,
                self.group_name,
                self.consumer_name,
                min_idle_time=self.pending_idle_ms,
                start_id="0-0",
                count=10,
            )
        except Exception as exc:
            self.metrics.last_error = str(exc)
            logger.warning(f"Pending recovery failed: {exc}")
            return

        claimed = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else []
        self.metrics.redis_pending_claimed += len(claimed)
        for message_id, message_data in claimed:
            delivery_count = 1
            try:
                pending_info = await redis_client.xpending_range(
                    self.stream_name,
                    self.group_name,
                    min=message_id,
                    max=message_id,
                    count=1,
                )
                if pending_info:
                    delivery_count = int(pending_info[0].get("times_delivered", delivery_count))
            except Exception:
                pass

            state_dict = self.decode_stream_payload(message_data) or {}
            if delivery_count >= self.dead_letter_after_deliveries:
                await self.send_to_dead_letter(redis_client, message_id, state_dict, "max_deliveries_exceeded")
            else:
                await self.handle_redis_message(redis_client, message_id, message_data)

    async def run_redis_consumer_loop(self):
        """Active Redis Stream consumer loop using XREADGROUP and XACK."""
        if not HAS_REDIS:
            logger.error("redis-py not installed. Cannot start Redis stream loop.")
            return

        r = redis_async.from_url(self.redis_url)

        # Create consumer group if not existing
        try:
            await r.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
            logger.info(f"Created Redis stream consumer group {self.group_name} on {self.stream_name}")
        except Exception:
            pass  # Group already exists

        logger.info(f"Started M4 Redis consumer loop [{self.consumer_name}] on stream '{self.stream_name}'")

        while True:
            try:
                await self.recover_pending_messages(r)

                # Read pending/new messages using XREADGROUP
                streams = await r.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_name: ">"},
                    count=10,
                    block=2000
                )

                if streams:
                    for stream, messages in streams:
                        for message_id, message_data in messages:
                            await self.handle_redis_message(r, message_id, message_data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Redis consumer loop: {e}")
                await asyncio.sleep(2.0)

        await r.aclose()

    async def close(self):
        await self.client.aclose()


if __name__ == "__main__":
    worker = M4Worker()
    asyncio.run(worker.run_redis_consumer_loop())

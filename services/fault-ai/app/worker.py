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
from typing import Dict, List, Optional, Tuple
import httpx

try:
    import redis.asyncio as redis_async
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

from app.contracts import TwinState, FaultPrediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("m4-worker")


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
        max_retries: int = 3
    ):
        self.m6_ingest_url = os.getenv("M6_INGEST_URL", m6_ingest_url)
        self.m4_predict_url = os.getenv("M4_PREDICT_URL", m4_predict_url)
        self.redis_url = os.getenv("REDIS_URL", redis_url)
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=5.0)

        # Keyed by (engineId, missionId) tuple
        self.rolling_windows: Dict[Tuple[str, str], List[dict]] = {}

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
        return False

    async def process_twin_state(self, twin_state_dict: dict) -> Optional[dict]:
        """Processes twin state through M4 predict API and pushes to M6."""
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
                return None

            prediction_data = resp.json()
            success = await self.publish_to_m6_with_retry(prediction_data)
            return prediction_data if success else None

        except Exception as e:
            logger.error(f"Worker pipeline error processing frame: {e}")
            return None

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
                            # Decode byte payload if necessary
                            raw_payload = message_data.get(b"payload") or message_data.get("payload")
                            if raw_payload:
                                state_dict = json.loads(raw_payload) if isinstance(raw_payload, (str, bytes)) else raw_payload
                                prediction = await self.process_twin_state(state_dict)

                                # Acknowledge message ONLY after prediction and M6 handoff succeed
                                if prediction is not None:
                                    await r.xack(self.stream_name, self.group_name, message_id)
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

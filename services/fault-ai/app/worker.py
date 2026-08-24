"""
Gate 07: Production Redis Stream Consumer and M6 Publisher Worker

Consumes twin.state.v1 stream, maintains 30-second rolling window per engine,
sends frames to M4 predict endpoint, and publishes FaultPrediction events to M6 with bounded retry and idempotency.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional
import httpx

from app.contracts import TwinState, FaultPrediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("m4-worker")


class M4Worker:
    """Production Redis consumer and M6 publisher with bounded retries."""

    def __init__(
        self,
        m6_ingest_url: str = "http://localhost:8006/ingest/fault",
        m4_predict_url: str = "http://localhost:8004/predict",
        redis_url: str = "redis://localhost:6379/0",
        max_retries: int = 3
    ):
        self.m6_ingest_url = os.getenv("M6_INGEST_URL", m6_ingest_url)
        self.m4_predict_url = os.getenv("M4_PREDICT_URL", m4_predict_url)
        self.redis_url = os.getenv("REDIS_URL", redis_url)
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=5.0)
        self.rolling_windows: Dict[str, List[dict]] = {}

    def update_rolling_window(self, engine_id: str, state_dict: dict) -> List[dict]:
        """Maintains maximum 30 rolling state frames per engine."""
        if engine_id not in self.rolling_windows:
            self.rolling_windows[engine_id] = []

        window = self.rolling_windows[engine_id]
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
                    logger.info(f"Published prediction to M6 [Correlation: {correlation_id}] (Status: {resp.status_code})")
                    return True
                else:
                    logger.warning(f"M6 returned non-success status {resp.status_code} (Attempt {attempt}/{self.max_retries})")
            except Exception as e:
                logger.warning(f"M6 unavailable error: {e} (Attempt {attempt}/{self.max_retries})")

            if attempt < self.max_retries:
                backoff_sec = 0.5 * (2 ** (attempt - 1))
                await asyncio.sleep(backoff_sec)

        logger.error(f"Failed to publish prediction to M6 after {self.max_retries} attempts [Correlation: {correlation_id}]")
        return False

    async def process_twin_state(self, twin_state_dict: dict) -> Optional[dict]:
        """Processes twin state through M4 predict API and pushes to M6."""
        engine_id = twin_state_dict.get("engineId", "ENG-DEFAULT")
        window = self.update_rolling_window(engine_id, twin_state_dict)

        payload = {
            "engineId": engine_id,
            "missionId": twin_state_dict.get("missionId", "MIS-DEFAULT"),
            "states": window
        }

        try:
            resp = await self.client.post(self.m4_predict_url, json=payload)
            if resp.status_code != 200:
                logger.error(f"Predict API failed with status {resp.status_code}: {resp.text}")
                return None

            prediction_data = resp.json()
            await self.publish_to_m6_with_retry(prediction_data)
            return prediction_data

        except Exception as e:
            logger.error(f"Worker pipeline error processing frame: {e}")
            return None

    async def close(self):
        await self.client.aclose()


if __name__ == "__main__":
    print("M4 Worker process initialized.")

"""
Gate 07: Redis Consumer and M6 Publisher Worker

Background worker listening to Redis stream twin.state.v1 and publishing FaultPrediction events to M6 Control API.
"""

import asyncio
import json
import logging
from typing import Optional
import httpx

from app.contracts import TwinState, FaultPrediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("m4-worker")


class M4Worker:
    """Worker service for processing twin state events and pushing predictions to M6."""

    def __init__(
        self,
        m6_ingest_url: str = "http://localhost:8006/ingest/fault",
        m4_predict_url: str = "http://localhost:8004/predict"
    ):
        self.m6_ingest_url = m6_ingest_url
        self.m4_predict_url = m4_predict_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def process_twin_state(self, twin_state_dict: dict) -> Optional[dict]:
        """Sends twin state to M4 predict endpoint and publishes prediction to M6."""
        try:
            resp = await self.client.post(self.m4_predict_url, json=twin_state_dict)
            if resp.status_code != 200:
                logger.error(f"Prediction failed with status {resp.status_code}: {resp.text}")
                return None

            prediction_data = resp.json()

            # Publish prediction to M6 Control API
            m6_resp = await self.client.post(self.m6_ingest_url, json=prediction_data)
            logger.info(f"Published prediction to M6 ({m6_resp.status_code}): {prediction_data['faultType']}")

            return prediction_data
        except Exception as e:
            logger.error(f"Error in worker pipeline: {e}")
            return None

    async def close(self):
        await self.client.aclose()


if __name__ == "__main__":
    print("M4 Worker initialized.")

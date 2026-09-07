"""M3/M5 boundary adapter with durable outbox and ACK only after both M6 accepts."""
import asyncio
import hashlib
import json
import logging
import os
import time
from pathlib import Path

import httpx
import redis.asyncio as redis
from redis.exceptions import ResponseError

log = logging.getLogger("m3-m5-handoff")
logging.basicConfig(level=logging.INFO)


class HandoffWorker:
    stream = "twin.state.v1"
    group = "m3-m5-handoff"
    consumer = "m3-m5-worker-1"

    def __init__(self, client, http):
        self.redis = client
        self.http = http
        self.m3 = os.getenv("M3_URL", "http://health-monitor:8003")
        self.m5 = os.getenv("M5_URL", "http://rul-validation:8005")
        self.m6 = os.getenv("M6_URL", "http://control-api:4000")

    async def handle(self, message_id, fields):
        raw = fields.get("payload") or fields.get(b"payload")
        state = json.loads(raw)
        # A logical event is scoped by all IDs and source time. Cache complete outputs
        # before any external write, so a crash cannot generate a conflicting retry.
        identity = [state[k] for k in ("engineId", "missionId", "correlationId", "stateTime")]
        event_id = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        key = f"integration:outbox:{event_id}"
        cached = await self.redis.get(key)
        if cached:
            outbox = json.loads(cached)
        else:
            response = await self.http.post(f"{self.m3}/evaluate", json=state)
            response.raise_for_status()
            health = response.json()
            response = await self.http.post(f"{self.m5}/estimate", json={"state": state, "health": health})
            response.raise_for_status()
            outbox = {"health": health, "rul": response.json()}
            await self.redis.set(key, json.dumps(outbox))
        for kind, payload in outbox.items():
            response = await self.http.post(
                f"{self.m6}/ingest/{kind}", json=payload,
                headers={"X-Idempotency-Key": f"{kind}:{event_id}"},
            )
            if response.status_code != 202:
                raise RuntimeError(f"M6 {kind} returned {response.status_code}: {response.text}")
            log.info(json.dumps({"event": "handoff.accepted", "kind": kind,
                **{k: payload[k] for k in ("engineId", "missionId", "correlationId", "producerVersion")}}))
        await self.redis.xack(self.stream, self.group, message_id)
        # Keep outbox through restart/replay; local demo reset clears Redis explicitly.

    async def process(self, messages):
        for message_id, fields in messages:
            try:
                await self.handle(message_id, fields)
            except (ValueError, KeyError, TypeError) as exc:
                await self.redis.xadd("integration.dlq.v1", {
                    "sourceMessageId": str(message_id), "error": str(exc), "payload": str(fields),
                })
                await self.redis.xack(self.stream, self.group, message_id)
            except Exception:
                log.exception("Handoff failed; message remains pending: %s", message_id)

    async def run(self):
        try:
            await self.redis.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        cursor = "0-0"
        while True:
            try:
                pending = await self.redis.xautoclaim(self.stream, self.group, self.consumer,
                    min_idle_time=10000, start_id=cursor, count=10)
                cursor = pending[0]
                await self.process(pending[1])
                rows = await self.redis.xreadgroup(self.group, self.consumer,
                    {self.stream: ">"}, count=10, block=1000)
                for _, messages in rows:
                    await self.process(messages)
                Path("/tmp/worker-heartbeat").write_text(str(time.time()))
            except Exception:
                log.exception("Redis worker loop failed")
                await asyncio.sleep(2)


async def main():
    async with redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"), decode_responses=True) as client:
        async with httpx.AsyncClient(timeout=10) as http:
            await HandoffWorker(client, http).run()


if __name__ == "__main__":
    asyncio.run(main())

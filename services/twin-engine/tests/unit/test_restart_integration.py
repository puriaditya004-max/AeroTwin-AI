import json
from datetime import datetime, timezone
import pytest
from fakeredis.aioredis import FakeRedis
from app.worker import M2Worker
from storage.checkpoint import RedisCheckpointStore
from stream.publisher import TwinStatePublisher
from test_processor import sample_frame

@pytest.mark.asyncio
async def test_worker_restart_does_not_republish_and_api_reads_durable_state(monkeypatch):
    redis = FakeRedis(decode_responses=True)
    worker = M2Worker()
    stream = worker.settings.streams.input
    group = worker.settings.streams.group
    await redis.xgroup_create(stream, group, id="0", mkstream=True)
    payload = sample_frame()
    message_id = await redis.xadd(stream, {"payload": json.dumps(payload)})
    rows = await redis.xreadgroup(group, worker.settings.streams.consumer, {stream: ">"})
    store = RedisCheckpointStore(redis)
    publisher = TwinStatePublisher(redis, worker.settings.streams.output)
    await worker._process_streams(redis, publisher, store, rows)
    assert await redis.xlen(worker.settings.streams.output) == 1
    assert (await redis.xpending(stream, group))["pending"] == 0
    # Simulate delivery again after a process restart.
    await M2Worker()._process_streams(redis, publisher, store, rows)
    assert await redis.xlen(worker.settings.streams.output) == 1
    from app import main
    monkeypatch.setattr(main.redis_async, "from_url", lambda *a, **k: redis)
    state = await main.read_latest(mission_id=payload["missionId"])
    assert state.correlationId == payload["correlationId"]
    assert state.model_extra["sensors"] == payload["sensors"] or state.model_extra["sensors"]["rpm"] == payload["sensors"]["rpm"]

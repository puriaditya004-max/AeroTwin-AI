import importlib.util
import json
from pathlib import Path
import pytest
import httpx
from fakeredis.aioredis import FakeRedis

spec = importlib.util.spec_from_file_location("handoff", Path(__file__).with_name("worker.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.asyncio
async def test_partial_handoff_retries_identical_outbox_after_restart():
    redis = FakeRedis(decode_responses=True)
    state = {"engineId":"E", "missionId":"M", "correlationId":"C", "stateTime":"2026-09-07T00:00:00Z"}
    calls = []
    fail = True
    async def handler(request):
        nonlocal fail
        payload = json.loads(request.content)
        calls.append((request.url.path, payload, request.headers.get("X-Idempotency-Key")))
        if request.url.path in ("/evaluate", "/estimate"):
            return httpx.Response(200, json={**state, "producerVersion":"test"})
        if request.url.path == "/ingest/rul" and fail:
            fail = False
            return httpx.Response(503, json={})
        return httpx.Response(202, json={"duplicate": True})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        worker = module.HandoffWorker(redis,http)
        await redis.xgroup_create(worker.stream,worker.group,id="0",mkstream=True)
        mid = await redis.xadd(worker.stream,{"payload":json.dumps(state)})
        await redis.xreadgroup(worker.group,worker.consumer,{worker.stream:">"})
        with pytest.raises(RuntimeError): await worker.handle(mid,{"payload":json.dumps(state)})
        assert (await redis.xpending(worker.stream,worker.group))["pending"] == 1
        await module.HandoffWorker(redis,http).handle(mid,{"payload":json.dumps(state)})
        assert (await redis.xpending(worker.stream,worker.group))["pending"] == 0
        assert sum(c[0]=="/evaluate" for c in calls)==1
        assert sum(c[0]=="/estimate" for c in calls)==1
        health = [c for c in calls if c[0]=="/ingest/health"]
        assert health[0] == health[1]

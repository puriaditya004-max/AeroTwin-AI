import asyncio

try:
    import redis.asyncio as redis_async
except ImportError:  # pragma: no cover
    redis_async = None

from app.logging import log_event
from app.processor import TwinProcessor
from app.settings import get_settings
from ingest.consumer import decode_stream_payload
from storage.checkpoint import InMemoryCheckpointStore, RedisCheckpointStore
from stream.publisher import TwinStatePublisher


class M2Worker:
    def __init__(self):
        self.settings = get_settings()
        self.checkpoint = InMemoryCheckpointStore()
        self.processor = TwinProcessor(self.settings, self.checkpoint)

    async def run(self) -> None:
        if redis_async is None:
            raise RuntimeError("redis-py is required for M2 worker")

        redis_client = redis_async.from_url(self.settings.redisUrl)
        publisher = TwinStatePublisher(redis_client, self.settings.streams.output)
        durable_checkpoint = RedisCheckpointStore(redis_client)

        try:
            await redis_client.xgroup_create(
                self.settings.streams.input,
                self.settings.streams.group,
                id="0",
                mkstream=True,
            )
            log_event("consumer_group_created", stream=self.settings.streams.input, group=self.settings.streams.group)
        except Exception:
            log_event("consumer_group_exists", stream=self.settings.streams.input, group=self.settings.streams.group)

        log_event("worker_started", inputStream=self.settings.streams.input, outputStream=self.settings.streams.output)
        while True:
            try:
                streams = await self._read_pending(redis_client)
                if not streams:
                    streams = await redis_client.xreadgroup(
                        groupname=self.settings.streams.group,
                        consumername=self.settings.streams.consumer,
                        streams={self.settings.streams.input: ">"},
                        count=10,
                        block=2000,
                    )
                await self._process_streams(redis_client, publisher, durable_checkpoint, streams)
                __import__("pathlib").Path("/tmp/m2-heartbeat").write_text(str(__import__("time").time()))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log_event("worker_error", error=str(exc))
                await asyncio.sleep(2.0)

        await redis_client.aclose()

    async def _read_pending(self, redis_client):
        try:
            response = await redis_client.xautoclaim(
                self.settings.streams.input,
                self.settings.streams.group,
                self.settings.streams.consumer,
                min_idle_time=self.settings.sync.pendingIdleMs,
                start_id="0-0",
                count=10,
            )
        except Exception as exc:
            log_event("pending_claim_skipped", error=str(exc))
            return []

        messages = []
        if isinstance(response, (list, tuple)) and len(response) >= 2:
            messages = response[1]
        if not messages:
            return []
        log_event("pending_claimed", count=len(messages), stream=self.settings.streams.input)
        return [(self.settings.streams.input, messages)]

    async def _process_streams(self, redis_client, publisher, durable_checkpoint, streams) -> None:
        import hashlib
        import json
        from app.contracts import TelemetryFrame
        for _, messages in streams:
            for message_id, fields in messages:
                try:
                    payload = decode_stream_payload(fields)
                    frame = TelemetryFrame.model_validate(payload)
                except Exception as exc:
                    await redis_client.xadd("telemetry.dlq.v1", {"sourceMessageId": str(message_id), "error": str(exc)})
                    await redis_client.xack(self.settings.streams.input, self.settings.streams.group, message_id)
                    continue
                identity = self.processor.dedupe.key_for(frame)
                done_key = "m2:done:" + hashlib.sha256(identity.encode()).hexdigest()
                if await redis_client.exists(done_key):
                    await redis_client.xack(self.settings.streams.input, self.settings.streams.group, message_id)
                    continue
                window_key = "m2:window:" + hashlib.sha256(json.dumps([frame.engineId, frame.missionId]).encode()).hexdigest()
                previous = await redis_client.get(window_key)
                # Rebuild context from the committed rolling window, including on retry.
                self.processor = TwinProcessor(self.settings, self.checkpoint)
                if previous:
                    for old in json.loads(previous):
                        old_frame = TelemetryFrame.model_validate(old)
                        self.processor.windows.add(old_frame)
                        self.processor.reorder.accept(old_frame)
                result = self.processor.process_payload(payload, str(message_id))
                if result.state is None:
                    await redis_client.xack(self.settings.streams.input, self.settings.streams.group, message_id)
                    continue
                state = result.state
                state_key = durable_checkpoint._state_key(state.engineId, state.missionId)
                window = self.processor.windows.latest(state.engineId, state.missionId)
                async with redis_client.pipeline(transaction=True) as tx:
                    tx.xadd(self.settings.streams.output, {"payload": state.model_dump_json(exclude_none=True), "correlationId": state.correlationId})
                    tx.set(state_key, state.model_dump_json(exclude_none=True))
                    tx.sadd(durable_checkpoint._index_key(), state_key)
                    tx.set(durable_checkpoint._stream_key(), str(message_id))
                    tx.set(window_key, json.dumps([f.model_dump(mode="json") for f in window]))
                    tx.set(done_key, "1")
                    tx.xack(self.settings.streams.input, self.settings.streams.group, message_id)
                    await tx.execute()
                log_event("state_published", engineId=state.engineId, missionId=state.missionId,
                          correlationId=state.correlationId, producerVersion=state.producerVersion)


if __name__ == "__main__":
    asyncio.run(M2Worker().run())

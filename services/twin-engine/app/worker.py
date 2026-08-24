import asyncio

try:
    import redis.asyncio as redis_async
except ImportError:  # pragma: no cover
    redis_async = None

from app.logging import log_event
from app.processor import TwinProcessor
from app.settings import get_settings
from ingest.consumer import decode_stream_payload
from storage.checkpoint import InMemoryCheckpointStore
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
                streams = await redis_client.xreadgroup(
                    groupname=self.settings.streams.group,
                    consumername=self.settings.streams.consumer,
                    streams={self.settings.streams.input: ">"},
                    count=10,
                    block=2000,
                )
                for _, messages in streams:
                    for message_id, message_data in messages:
                        payload = decode_stream_payload(message_data)
                        if payload is None:
                            await redis_client.xack(self.settings.streams.input, self.settings.streams.group, message_id)
                            continue
                        result = self.processor.process_payload(payload, str(message_id))
                        if result.state is not None:
                            output_id = await publisher.publish(result.state)
                            self.processor.metrics["statesPublished"] += 1
                            log_event(
                                "state_published",
                                engineId=result.state.engineId,
                                missionId=result.state.missionId,
                                correlationId=result.state.correlationId,
                                stateQuality=result.state.stateQuality.value,
                                syncLagMs=result.state.syncLagMs,
                                outputStream=self.settings.streams.output,
                                outputMessageId=output_id,
                            )
                        if result.accepted or result.reason in {"schema_validation", "late"}:
                            await redis_client.xack(self.settings.streams.input, self.settings.streams.group, message_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log_event("worker_error", error=str(exc))
                await asyncio.sleep(2.0)

        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(M2Worker().run())

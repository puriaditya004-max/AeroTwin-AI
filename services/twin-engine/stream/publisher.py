import json

from app.contracts import TwinState


class TwinStatePublisher:
    def __init__(self, redis_client, stream_name: str):
        self.redis_client = redis_client
        self.stream_name = stream_name

    async def publish(self, state: TwinState) -> str:
        payload = state.model_dump(mode="json")
        message_id = await self.redis_client.xadd(
            self.stream_name,
            {"payload": json.dumps(payload), "correlationId": state.correlationId},
        )
        if isinstance(message_id, bytes):
            return message_id.decode("utf-8")
        return str(message_id)

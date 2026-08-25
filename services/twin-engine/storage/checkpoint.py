import json

from app.contracts import TwinState


class InMemoryCheckpointStore:
    def __init__(self):
        self._states: dict[tuple[str, str], TwinState] = {}
        self.last_stream_id: str | None = None

    def save(self, state: TwinState, stream_id: str | None = None) -> None:
        self._states[(state.engineId, state.missionId)] = state
        if stream_id is not None:
            self.last_stream_id = stream_id

    def latest(self, engine_id: str | None = None, mission_id: str | None = None) -> TwinState | None:
        if engine_id and mission_id:
            return self._states.get((engine_id, mission_id))
        if engine_id:
            matches = [state for (eng, _), state in self._states.items() if eng == engine_id]
            return max(matches, key=lambda item: item.stateTime, default=None)
        return max(self._states.values(), key=lambda item: item.stateTime, default=None)

    def all_states(self) -> list[TwinState]:
        return list(self._states.values())


class RedisCheckpointStore:
    """Durable latest-state checkpoint used by the Redis worker."""

    def __init__(self, redis_client, key_prefix: str = "m2:twin"):
        self.redis_client = redis_client
        self.key_prefix = key_prefix

    def _state_key(self, engine_id: str, mission_id: str) -> str:
        return f"{self.key_prefix}:state:{engine_id}:{mission_id}"

    def _index_key(self) -> str:
        return f"{self.key_prefix}:state-index"

    def _stream_key(self) -> str:
        return f"{self.key_prefix}:last-stream-id"

    async def save(self, state: TwinState, stream_id: str | None = None) -> None:
        payload = state.model_dump_json()
        state_key = self._state_key(state.engineId, state.missionId)
        await self.redis_client.set(state_key, payload)
        await self.redis_client.sadd(self._index_key(), state_key)
        if stream_id is not None:
            await self.redis_client.set(self._stream_key(), stream_id)

    async def latest(self, engine_id: str, mission_id: str) -> TwinState | None:
        raw = await self.redis_client.get(self._state_key(engine_id, mission_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return TwinState.model_validate(json.loads(raw))

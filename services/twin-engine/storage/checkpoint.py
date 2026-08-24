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

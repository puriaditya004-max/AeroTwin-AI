from collections import defaultdict, deque
from datetime import timedelta

from app.contracts import TelemetryFrame


class WindowStore:
    def __init__(self, window_seconds: int, max_samples: int):
        self.window_seconds = window_seconds
        self.max_samples = max_samples
        self._windows: dict[tuple[str, str], deque[TelemetryFrame]] = defaultdict(
            lambda: deque(maxlen=max_samples)
        )

    def add(self, frame: TelemetryFrame) -> list[TelemetryFrame]:
        key = (frame.engineId, frame.missionId)
        window = self._windows[key]
        window.append(frame)
        cutoff = frame.timestamp - timedelta(seconds=self.window_seconds)
        while window and window[0].timestamp < cutoff:
            window.popleft()
        ordered = sorted(window, key=lambda item: item.timestamp)
        return ordered

    def latest(self, engine_id: str, mission_id: str) -> list[TelemetryFrame]:
        return list(self._windows.get((engine_id, mission_id), []))

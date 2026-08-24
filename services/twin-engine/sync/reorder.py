from datetime import datetime

from app.contracts import TelemetryFrame


class ReorderGuard:
    """Rejects frames that are older than the configured event-time tolerance."""

    def __init__(self, tolerance_ms: int):
        self.tolerance_ms = tolerance_ms
        self._latest_by_partition: dict[tuple[str, str], datetime] = {}

    def accept(self, frame: TelemetryFrame) -> bool:
        key = (frame.engineId, frame.missionId)
        latest = self._latest_by_partition.get(key)
        if latest is None:
            self._latest_by_partition[key] = frame.timestamp
            return True

        if frame.timestamp >= latest:
            self._latest_by_partition[key] = frame.timestamp
            return True

        late_ms = (latest - frame.timestamp).total_seconds() * 1000.0
        return late_ms <= self.tolerance_ms

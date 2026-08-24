from collections import OrderedDict

from app.contracts import TelemetryFrame


class DedupeCache:
    def __init__(self, max_items: int = 5000):
        self.max_items = max_items
        self._seen: OrderedDict[str, None] = OrderedDict()

    @staticmethod
    def key_for(frame: TelemetryFrame) -> str:
        return "|".join(
            [
                frame.engineId,
                frame.missionId,
                frame.timestamp.isoformat(),
                frame.correlationId,
            ]
        )

    def seen_or_add(self, frame: TelemetryFrame) -> bool:
        key = self.key_for(frame)
        if key in self._seen:
            self._seen.move_to_end(key)
            return True
        self._seen[key] = None
        if len(self._seen) > self.max_items:
            self._seen.popitem(last=False)
        return False

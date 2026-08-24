from pydantic import ValidationError

from app.contracts import TelemetryFrame, TwinState
from app.logging import log_event
from app.settings import Settings
from state.estimator import TwinEstimator
from state.window import WindowStore
from storage.checkpoint import InMemoryCheckpointStore
from sync.dedupe import DedupeCache
from sync.reorder import ReorderGuard


class FrameProcessResult:
    def __init__(self, state: TwinState | None, accepted: bool, reason: str):
        self.state = state
        self.accepted = accepted
        self.reason = reason


class TwinProcessor:
    def __init__(self, settings: Settings, checkpoint: InMemoryCheckpointStore | None = None):
        self.settings = settings
        self.dedupe = DedupeCache(max_items=settings.sync.idempotencyTtl)
        self.reorder = ReorderGuard(settings.sync.reorderToleranceMs)
        self.windows = WindowStore(settings.sync.primaryWindowSeconds, settings.sync.maxWindowSamples)
        self.estimator = TwinEstimator(
            settings.estimator,
            settings.sync.primaryWindowSeconds,
            settings.sync.staleAfterMs,
        )
        self.checkpoint = checkpoint or InMemoryCheckpointStore()
        self.metrics = {
            "framesConsumed": 0,
            "framesRejected": 0,
            "framesDeduped": 0,
            "lateFrames": 0,
            "statesPublished": 0,
        }

    def process_payload(self, payload: dict, stream_id: str | None = None) -> FrameProcessResult:
        self.metrics["framesConsumed"] += 1
        try:
            frame = TelemetryFrame.model_validate(payload)
        except ValidationError as exc:
            self.metrics["framesRejected"] += 1
            log_event("frame_rejected", reason="schema_validation", errors=exc.errors())
            return FrameProcessResult(None, False, "schema_validation")

        log_context = {
            "engineId": frame.engineId,
            "missionId": frame.missionId,
            "correlationId": frame.correlationId,
            "sourceTime": frame.timestamp.isoformat(),
            "qualityFlag": frame.qualityFlag.value,
        }

        if self.dedupe.seen_or_add(frame):
            self.metrics["framesDeduped"] += 1
            log_event("frame_deduped", reason="duplicate_idempotency_key", **log_context)
            return FrameProcessResult(None, True, "duplicate")

        if not self.reorder.accept(frame):
            self.metrics["lateFrames"] += 1
            self.metrics["framesRejected"] += 1
            log_event("frame_rejected", reason="beyond_reorder_tolerance", **log_context)
            return FrameProcessResult(None, False, "late")

        window = self.windows.add(frame)
        state = self.estimator.estimate(frame, window)
        self.checkpoint.save(state, stream_id)
        log_event(
            "state_estimated",
            stateTime=state.stateTime.isoformat(),
            load=state.load,
            stateQuality=state.stateQuality.value,
            syncLagMs=state.syncLagMs,
            **log_context,
        )
        return FrameProcessResult(state, True, "accepted")

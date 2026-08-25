from pydantic import ValidationError
import statistics

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
            settings.engineProfile,
        )
        self.checkpoint = checkpoint or InMemoryCheckpointStore()
        self._sync_lag_samples: list[float] = []
        self.metrics = {
            "framesConsumed": 0,
            "framesRejected": 0,
            "framesDeduped": 0,
            "lateFrames": 0,
            "statesPublished": 0,
            "publishFailures": 0,
            "lastSyncLagMs": None,
        }

    def metrics_snapshot(self) -> dict:
        snapshot = dict(self.metrics)
        samples = self._sync_lag_samples[-500:]
        if samples:
            snapshot["averageSyncLagMs"] = round(float(statistics.mean(samples)), 3)
            sorted_samples = sorted(samples)
            index = min(len(sorted_samples) - 1, int(0.95 * (len(sorted_samples) - 1)))
            snapshot["p95SyncLagMs"] = round(float(sorted_samples[index]), 3)
        else:
            snapshot["averageSyncLagMs"] = None
            snapshot["p95SyncLagMs"] = None
        return snapshot

    def record_publish_success(self) -> None:
        self.metrics["statesPublished"] += 1

    def record_publish_failure(self) -> None:
        self.metrics["publishFailures"] += 1

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
        if state.syncLagMs is not None:
            self.metrics["lastSyncLagMs"] = state.syncLagMs
            self._sync_lag_samples.append(state.syncLagMs)
            if len(self._sync_lag_samples) > 500:
                self._sync_lag_samples = self._sync_lag_samples[-500:]
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

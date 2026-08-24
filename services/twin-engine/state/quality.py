from datetime import datetime

from app.contracts import QualityFlag, StateQuality, TelemetryFrame


def assess_state_quality(
    frame: TelemetryFrame,
    processing_time: datetime,
    stale_after_ms: int,
    accepted_sample_count: int,
) -> StateQuality:
    lag_ms = max(0.0, (processing_time - frame.timestamp).total_seconds() * 1000.0)
    if lag_ms > stale_after_ms:
        return StateQuality.STALE
    if frame.qualityFlag != QualityFlag.OK or accepted_sample_count < 2:
        return StateQuality.DEGRADED
    return StateQuality.GOOD

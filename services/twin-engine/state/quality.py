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
    sensor_quality = frame.sensors.sensorQuality or {}
    has_bad_sensor_quality = any(quality.status.value != "OK" for quality in sensor_quality.values())
    has_missing_optional_sensors = any(
        getattr(frame.sensors, name) in (None, [])
        for name in (
            "chtCylindersC",
            "egtCylindersC",
            "alternatorVoltageV",
            "alternatorCurrentA",
            "batteryVoltageV",
            "injectionTimingDeg",
        )
    )
    if frame.qualityFlag != QualityFlag.OK or accepted_sample_count < 2 or has_bad_sensor_quality or has_missing_optional_sensors:
        return StateQuality.DEGRADED
    return StateQuality.GOOD

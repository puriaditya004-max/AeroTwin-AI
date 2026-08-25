from datetime import datetime, timezone

from app.contracts import Margins, TelemetryFrame, TwinState
from app.settings import EngineProfile, EstimatorSettings
from state.features import build_derived_features
from state.quality import assess_state_quality


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class TwinEstimator:
    def __init__(self, settings: EstimatorSettings, window_seconds: int, stale_after_ms: int, profile: EngineProfile):
        self.settings = settings
        self.window_seconds = window_seconds
        self.stale_after_ms = stale_after_ms
        self.profile = profile

    def estimate(self, frame: TelemetryFrame, window: list[TelemetryFrame]) -> TwinState:
        now = datetime.now(timezone.utc)
        weights = self.settings.loadWeights
        rpm_norm = _clamp(frame.sensors.rpm / self.settings.maxRpm, 0.0, 1.0)
        fuel_norm = _clamp(frame.sensors.fuelFlowLph / self.settings.maxFuelFlowLph, 0.0, 1.0)
        throttle_norm = _clamp(frame.sensors.throttlePct / 100.0, 0.0, 1.0)
        load = 100.0 * (
            weights["throttle"] * throttle_norm
            + weights["rpm"] * rpm_norm
            + weights["fuelFlow"] * fuel_norm
        )

        hottest_temp = max([frame.sensors.coolantTempC, frame.sensors.oilTempC] + (frame.sensors.chtCylindersC or []))
        pressure_min = self.profile.pressure["oilMinKpa"] + self.profile.pressure["loadSlopeKpa"] * load
        margins = Margins(
            tempMarginC=round(self.profile.temperature["chtCriticalC"] - hottest_temp, 3),
            pressureMarginKpa=round(frame.sensors.oilPressureKpa - pressure_min, 3),
            vibrationMarginMmS=round(self.profile.vibration["criticalMmS"] - frame.sensors.vibrationMmS, 3),
        )
        sync_lag_ms = max(0.0, (now - frame.timestamp).total_seconds() * 1000.0)
        state_quality = assess_state_quality(frame, now, self.stale_after_ms, len(window))

        return TwinState(
            engineId=frame.engineId,
            missionId=frame.missionId,
            correlationId=frame.correlationId,
            stateTime=frame.timestamp,
            schemaVersion="2.0.0" if frame.schemaVersion.startswith("2") else "1.0.0",
            producerVersion="m2-twin-engine@2.0.0",
            load=round(_clamp(load, 0.0, 100.0), 3),
            margins=margins,
            derivedFeatures=build_derived_features(window, self.window_seconds, self.settings, self.profile),
            stateQuality=state_quality,
            syncLagMs=round(sync_lag_ms, 3),
        )

from datetime import datetime, timezone

from app.contracts import Margins, TelemetryFrame, TwinState
from app.settings import EstimatorSettings
from state.features import build_derived_features
from state.quality import assess_state_quality


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class TwinEstimator:
    def __init__(self, settings: EstimatorSettings, window_seconds: int, stale_after_ms: int):
        self.settings = settings
        self.window_seconds = window_seconds
        self.stale_after_ms = stale_after_ms

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

        hottest_temp = max(frame.sensors.coolantTempC, frame.sensors.oilTempC)
        pressure_min = self.settings.baseOilPressureMinKpa + self.settings.loadOilPressureSlopeKpa * load
        margins = Margins(
            tempMarginC=round(self.settings.tempLimitC - hottest_temp, 3),
            pressureMarginKpa=round(frame.sensors.oilPressureKpa - pressure_min, 3),
            vibrationMarginMmS=round(self.settings.vibrationLimitMmS - frame.sensors.vibrationMmS, 3),
        )
        sync_lag_ms = max(0.0, (now - frame.timestamp).total_seconds() * 1000.0)
        state_quality = assess_state_quality(frame, now, self.stale_after_ms, len(window))

        return TwinState(
            engineId=frame.engineId,
            missionId=frame.missionId,
            correlationId=frame.correlationId,
            stateTime=frame.timestamp,
            producerVersion="m2-twin-engine@1.0.0",
            load=round(_clamp(load, 0.0, 100.0), 3),
            margins=margins,
            derivedFeatures=build_derived_features(window, self.window_seconds),
            stateQuality=state_quality,
            syncLagMs=round(sync_lag_ms, 3),
        )

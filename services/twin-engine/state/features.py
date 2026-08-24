import numpy as np

from app.contracts import DerivedFeatures, TelemetryFrame


def build_derived_features(window: list[TelemetryFrame], window_seconds: int) -> DerivedFeatures:
    if not window:
        return DerivedFeatures(
            rollingMeanRpm=0.0,
            rollingStdVibration=0.0,
            rateOfChangeOilTempCPerMin=0.0,
            sampleWindowSeconds=float(window_seconds),
        )

    rpm_values = np.array([frame.sensors.rpm for frame in window], dtype=float)
    vibration_values = np.array([frame.sensors.vibrationMmS for frame in window], dtype=float)

    oil_rate = 0.0
    if len(window) >= 2:
        first = window[0]
        last = window[-1]
        elapsed_min = max((last.timestamp - first.timestamp).total_seconds() / 60.0, 1e-9)
        oil_rate = (last.sensors.oilTempC - first.sensors.oilTempC) / elapsed_min

    return DerivedFeatures(
        rollingMeanRpm=round(float(np.mean(rpm_values)), 3),
        rollingStdVibration=round(float(np.std(vibration_values)), 3),
        rateOfChangeOilTempCPerMin=round(float(oil_rate), 3),
        sampleWindowSeconds=float(window_seconds),
    )

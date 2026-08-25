import numpy as np

from app.contracts import DerivedFeatures, TelemetryFrame
from app.settings import EngineProfile, EstimatorSettings


def _slope_per_min(values: list[float], window: list[TelemetryFrame]) -> float:
    if len(values) < 2 or len(window) < 2:
        return 0.0
    elapsed_min = max((window[-1].timestamp - window[0].timestamp).total_seconds() / 60.0, 1e-9)
    return (values[-1] - values[0]) / elapsed_min


def _stats(values: list[float]) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    arr = np.array(values, dtype=float)
    return round(float(np.max(arr)), 3), round(float(np.mean(arr)), 3), round(float(np.max(arr) - np.min(arr)), 3)


def build_derived_features(
    window: list[TelemetryFrame],
    window_seconds: int,
    estimator: EstimatorSettings | None = None,
    profile: EngineProfile | None = None,
) -> DerivedFeatures:
    if not window:
        return DerivedFeatures(
            rollingMeanRpm=0.0,
            rollingStdVibration=0.0,
            rateOfChangeOilTempCPerMin=0.0,
            sampleWindowSeconds=float(window_seconds),
            missingSensorRatio=1.0,
            stateConfidence=0.0,
            reasonCodes=["EMPTY_WINDOW"],
        )

    rpm_values = np.array([frame.sensors.rpm for frame in window], dtype=float)
    vibration_values = np.array([frame.sensors.vibrationMmS for frame in window], dtype=float)
    latest = window[-1]

    oil_rate = 0.0
    if len(window) >= 2:
        first = window[0]
        last = window[-1]
        elapsed_min = max((last.timestamp - first.timestamp).total_seconds() / 60.0, 1e-9)
        oil_rate = (last.sensors.oilTempC - first.sensors.oilTempC) / elapsed_min

    optional_names = [
        "chtCylindersC",
        "egtCylindersC",
        "alternatorVoltageV",
        "alternatorCurrentA",
        "batteryVoltageV",
        "injectionTimingDeg",
    ]
    missing_names = [name for name in optional_names if getattr(latest.sensors, name) in (None, [])]
    reason_codes = [f"MISSING_{name}" for name in missing_names]
    sensor_quality = latest.sensors.sensorQuality or {}
    reason_codes.extend(
        f"{name}_{quality.status.value}"
        for name, quality in sorted(sensor_quality.items())
        if quality.status.value != "OK"
    )
    missing_ratio = len(missing_names) / len(optional_names)
    invalid_ratio = sum(1 for quality in sensor_quality.values() if quality.status.value == "OUT_OF_RANGE") / max(
        len(sensor_quality), 1
    )

    cht_latest = latest.sensors.chtCylindersC or []
    egt_latest = latest.sensors.egtCylindersC or []
    cht_max, cht_mean, cht_spread = _stats(cht_latest)
    egt_max, egt_mean, egt_spread = _stats(egt_latest)
    cht_history = [max(frame.sensors.chtCylindersC) for frame in window if frame.sensors.chtCylindersC]
    egt_history = [max(frame.sensors.egtCylindersC) for frame in window if frame.sensors.egtCylindersC]

    oil_pressure_deviation = None
    fuel_flow_deviation = None
    injection_deviation = None
    alternator_margin = None
    battery_margin = None
    if estimator is not None:
        rpm_norm = min(1.0, max(0.0, latest.sensors.rpm / estimator.maxRpm))
        throttle_norm = min(1.0, max(0.0, latest.sensors.throttlePct / 100.0))
        expected_fuel = estimator.maxFuelFlowLph * (0.15 + 0.85 * throttle_norm)
        fuel_flow_deviation = round(latest.sensors.fuelFlowLph - expected_fuel, 3)
        expected_pressure = estimator.baseOilPressureMinKpa + estimator.loadOilPressureSlopeKpa * (rpm_norm * 100.0)
        oil_pressure_deviation = round(latest.sensors.oilPressureKpa - expected_pressure, 3)
    if profile is not None:
        if latest.sensors.injectionTimingDeg is not None:
            injection_deviation = round(
                latest.sensors.injectionTimingDeg - profile.injection["nominalTimingDeg"], 3
            )
        if latest.sensors.alternatorVoltageV is not None:
            alternator_margin = round(latest.sensors.alternatorVoltageV - profile.electrical["alternatorMinV"], 3)
        if latest.sensors.batteryVoltageV is not None:
            battery_margin = round(latest.sensors.batteryVoltageV - profile.electrical["batteryMinV"], 3)

    confidence = max(0.0, min(1.0, 1.0 - (0.6 * missing_ratio) - (0.4 * invalid_ratio)))

    return DerivedFeatures(
        rollingMeanRpm=round(float(np.mean(rpm_values)), 3),
        rollingStdVibration=round(float(np.std(vibration_values)), 3),
        rateOfChangeOilTempCPerMin=round(float(oil_rate), 3),
        sampleWindowSeconds=float(window_seconds),
        chtMaxC=cht_max,
        chtMeanC=cht_mean,
        chtSpreadC=cht_spread,
        chtSlopeCPerMin=round(float(_slope_per_min(cht_history, window)), 3) if cht_history else None,
        egtMaxC=egt_max,
        egtMeanC=egt_mean,
        egtSpreadC=egt_spread,
        egtSlopeCPerMin=round(float(_slope_per_min(egt_history, window)), 3) if egt_history else None,
        oilPressureDeviationKpa=oil_pressure_deviation,
        fuelFlowDeviationLph=fuel_flow_deviation,
        injectionTimingDeviationDeg=injection_deviation,
        alternatorVoltageMarginV=alternator_margin,
        batteryVoltageMarginV=battery_margin,
        vibrationRollingMeanMmS=round(float(np.mean(vibration_values)), 3),
        vibrationSlopeMmSPerMin=round(float(_slope_per_min(list(vibration_values), window)), 3),
        vibrationPeakMmS=round(float(np.max(vibration_values)), 3),
        missingSensorRatio=round(float(missing_ratio), 3),
        invalidSensorRatio=round(float(invalid_ratio), 3),
        stateConfidence=round(float(confidence), 3),
        reasonCodes=reason_codes,
    )

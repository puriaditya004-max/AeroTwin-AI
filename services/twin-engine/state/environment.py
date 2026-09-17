"""Environment-aware expected-value baseline for the SIH demonstrator.

This is deliberately a documented heuristic baseline, not a certified engine
physics model.  It converts the operating context already supplied by M1 into
expected sensor values so downstream services can reason about deviation rather
than comparing every flight to one fixed threshold.
"""

from dataclasses import dataclass

from app.contracts import Sensors


@dataclass(frozen=True)
class ExpectedValues:
    oil_temp_c: float
    coolant_temp_c: float
    oil_pressure_kpa: float
    vibration_mm_s: float


def expected_values(sensors: Sensors, load: float) -> ExpectedValues:
    """Return context-adjusted demonstrator baselines for one telemetry frame.

    Load is derived by M2 from throttle, RPM, and fuel flow.  Ambient
    temperature and altitude are then used as explicit environmental inputs.
    Coefficients are demo defaults that must be calibrated with engine data.
    """
    ambient_delta = sensors.ambientTempC - 15.0
    altitude_km = sensors.altitudeM / 1000.0

    return ExpectedValues(
        oil_temp_c=75.0 + (0.30 * load) + (0.35 * ambient_delta) + (0.8 * altitude_km),
        coolant_temp_c=75.0 + (0.35 * load) + (0.45 * ambient_delta) + (1.0 * altitude_km),
        oil_pressure_kpa=300.0 + (1.80 * load) - (4.0 * altitude_km) - (0.15 * ambient_delta),
        vibration_mm_s=1.0 + (0.035 * load) + (0.04 * altitude_km),
    )

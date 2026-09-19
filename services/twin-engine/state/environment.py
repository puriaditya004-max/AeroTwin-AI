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


# Demonstrator operating envelope. The expected-value coefficients above were
# only exercised (and should only be trusted) inside this range during
# calibration. Outside it, M4 should treat the deviation baseline as reduced
# confidence rather than a certified physical prediction — this mirrors the
# out-of-distribution guidance in the M2/M4 module doc.
ENVELOPE_ALTITUDE_M = (0.0, 6000.0)
ENVELOPE_AMBIENT_TEMP_C = (-20.0, 45.0)


def operating_envelope_reason_codes(sensors: Sensors) -> list[str]:
    """Return reason codes when altitude/ambient temperature fall outside the
    range the expected-value baseline was calibrated for.

    This does not block state estimation — M2 still emits a best-effort
    TwinState — but the reason codes let M4 (and any human reviewer) know the
    deviation numbers are extrapolated, not validated.
    """
    reasons: list[str] = []
    low, high = ENVELOPE_ALTITUDE_M
    if not (low <= sensors.altitudeM <= high):
        reasons.append("OUT_OF_RANGE_ALTITUDE")
    low, high = ENVELOPE_AMBIENT_TEMP_C
    if not (low <= sensors.ambientTempC <= high):
        reasons.append("OUT_OF_RANGE_AMBIENT_TEMP")
    return reasons


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

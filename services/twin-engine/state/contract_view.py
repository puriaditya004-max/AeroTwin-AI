"""Builds the external M2 digital-twin contract from a TwinState.

Output shape (see M2 module guide, section 2.2):

    {
      "aircraftId": "UAV-001",
      "engineId": "ENGINE-1",
      "state": {engineSpeed, thermalState, lubricationState,
                combustionState, vibrationState, overallState},
      "estimatedValues": {expectedOilTemperature, expectedOilPressure,
                          expectedVibration},
      "deviation": {oilTemperature, oilPressure, vibration}
    }

Units follow the SIH demo engine profile (deg C, kPa, mm/s).  Deviations are
signed (actual - expected).  Fields whose expected-value baseline is not
available are emitted as null rather than a fake zero.
"""

from typing import Optional

from app.contracts import (
    M2Deviation,
    M2EngineStateView,
    M2EstimatedValues,
    M2TwinContract,
    TwinState,
)

DEFAULT_AIRCRAFT_ID = "UAV-001"


def _round(value: Optional[float], digits: int = 3) -> Optional[float]:
    return None if value is None else round(float(value), digits)


def build_m2_contract(state: TwinState, default_aircraft_id: str = DEFAULT_AIRCRAFT_ID) -> M2TwinContract:
    if state.subsystemState is None:
        raise ValueError("TwinState has no subsystemState; it was produced by an older M2 version")

    derived = state.derivedFeatures
    sensors = (state.model_extra or {}).get("sensors") or {}
    rpm = sensors.get("rpm", derived.rollingMeanRpm)
    subsystem = state.subsystemState

    return M2TwinContract(
        aircraftId=state.aircraftId or default_aircraft_id,
        engineId=state.engineId,
        state=M2EngineStateView(
            engineSpeed=round(float(rpm)),
            thermalState=subsystem.thermalState,
            lubricationState=subsystem.lubricationState,
            combustionState=subsystem.combustionState,
            vibrationState=subsystem.vibrationState,
            overallState=subsystem.overallState,
        ),
        estimatedValues=M2EstimatedValues(
            expectedOilTemperature=_round(derived.expectedOilTempC),
            expectedOilPressure=_round(derived.expectedOilPressureKpa),
            expectedVibration=_round(derived.expectedVibrationMmS),
        ),
        deviation=M2Deviation(
            oilTemperature=_round(derived.oilTempDeviationC),
            oilPressure=_round(derived.oilPressureDeviationKpa),
            vibration=_round(derived.vibrationDeviationMmS),
        ),
    )

from app.contracts import Sensors
from state.environment import expected_values


def sensors(**overrides):
    values = {
        "rpm": 2400, "oilPressureKpa": 420, "oilTempC": 95,
        "coolantTempC": 98, "vibrationMmS": 3.0, "fuelFlowLph": 35,
        "throttlePct": 60, "altitudeM": 0, "ambientTempC": 15,
        "ambientPressureKpa": 101,
    }
    values.update(overrides)
    return Sensors.model_validate(values)


def test_hotter_ambient_conditions_raise_expected_temperatures():
    nominal = expected_values(sensors(ambientTempC=15), load=60)
    hot = expected_values(sensors(ambientTempC=35), load=60)

    assert hot.oil_temp_c > nominal.oil_temp_c
    assert hot.coolant_temp_c > nominal.coolant_temp_c


def test_higher_altitude_reduces_expected_oil_pressure():
    sea_level = expected_values(sensors(altitudeM=0), load=60)
    high_altitude = expected_values(sensors(altitudeM=5000), load=60)

    assert high_altitude.oil_pressure_kpa < sea_level.oil_pressure_kpa


def test_hot_high_altitude_cruise_is_compensated_by_the_baseline():
    hot_cruise = sensors(altitudeM=6500, ambientTempC=34)
    expected = expected_values(hot_cruise, load=75)

    # Values used by the no-fault M1 context scenario remain close to their
    # adjusted baseline and must not look like a raw-threshold overheat.
    assert abs(112 - expected.oil_temp_c) < 8
    assert abs(116 - expected.coolant_temp_c) < 8

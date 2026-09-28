"""Shared environment-compensation package (bundled for M4 container)."""
from . import altitude_model, ambient_model, normalization, operating_point
from .altitude_model import (
    compensate_baseline, altitude_compensated_baselines, density_altitude_ft, density_ratio,
    isa_temperature_c, pressure_altitude_ft, pressure_lapse_rate_hpa_per_kft, pressure_ratio, sensor_family,
)
from .ambient_model import (
    compensate_thermal_baseline, is_extreme_ambient, is_thermal_sensor, thermal_tolerance_scale,
)
from .normalization import (
    Deviation, FeatureScaler, deviation_report, is_valid_reading, normalized_deviation,
)
from .operating_point import (
    FlightPhase, OperatingPoint, SENSOR_SIGMA, build_operating_point, expected_baselines,
    sensor_sigma, transient_sigma_scale,
)

__version__ = "1.0.0"

"""
Gate 08: Scenario Tests for Five Mandatory Mission Families
- NONE
- OVERHEATING
- OIL_PRESSURE_DEGRADATION
- VIBRATION_MISFIRE
- SENSOR_FAULT
"""

import pytest
from training.build_dataset import generate_single_mission


@pytest.mark.parametrize("family", [
    "NONE",
    "OVERHEATING",
    "OIL_PRESSURE_DEGRADATION",
    "VIBRATION_MISFIRE",
    "SENSOR_FAULT"
])
def test_mission_generation(family):
    df, manifest = generate_single_mission(
        mission_id=f"TEST-{family}",
        scenario_family=family,
        num_samples=60,
        seed=123
    )
    assert len(df) == 60
    assert manifest["scenario_family"] == family
    assert "tempMarginC" in df.columns
    assert "pressureMarginKpa" in df.columns
    assert "vibrationMarginMmS" in df.columns

import sys
from pathlib import Path

import pytest


# Add M5 service directory to Python path
SERVICE_DIR = Path(__file__).resolve().parents[1]

if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


from app.feature_builder import (
    FEATURE_COLUMNS,
    build_features,
    get_feature_names,
)


VALID_INPUT = {
    "temperature": 80,
    "vibration": 2.5,
    "pressure": 1.2,
    "rpm": 3000,
    "load": 75,
    "health_index": 0.8,
}


def test_feature_order_is_deterministic():

    data = {
        "load": 75,
        "rpm": 3000,
        "temperature": 80,
        "health_index": 0.8,
        "pressure": 1.2,
        "vibration": 2.5,
    }

    result = build_features(data)

    assert list(result.columns) == FEATURE_COLUMNS


def test_feature_values_are_preserved():

    result = build_features(VALID_INPUT)

    assert result.loc[0, "temperature"] == 80
    assert result.loc[0, "vibration"] == 2.5
    assert result.loc[0, "pressure"] == 1.2
    assert result.loc[0, "rpm"] == 3000
    assert result.loc[0, "load"] == 75
    assert result.loc[0, "health_index"] == 0.8


def test_feature_names_are_correct():

    names = get_feature_names()

    assert names == [
        "temperature",
        "vibration",
        "pressure",
        "rpm",
        "load",
        "health_index",
    ]


def test_missing_feature_is_rejected():

    invalid_data = VALID_INPUT.copy()

    del invalid_data["temperature"]

    with pytest.raises(ValueError, match="Missing required features"):
        build_features(invalid_data)


def test_invalid_health_index_is_rejected():

    invalid_data = VALID_INPUT.copy()

    invalid_data["health_index"] = 1.5

    with pytest.raises(
        ValueError,
        match="health_index must be between 0.0 and 1.0",
    ):
        build_features(invalid_data)


def test_non_numeric_feature_is_rejected():

    invalid_data = VALID_INPUT.copy()

    invalid_data["rpm"] = "invalid"

    with pytest.raises(
        ValueError,
        match="Invalid numeric value",
    ):
        build_features(invalid_data)
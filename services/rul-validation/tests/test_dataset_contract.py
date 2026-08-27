import pytest

from training.dataset_contract import (
    ALL_COLUMNS,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    validate_dataset_columns,
)


def test_dataset_has_canonical_columns():
    columns = [
        "engine_id",
        "cycle",
        "temperature",
        "vibration",
        "pressure",
        "rpm",
        "load",
        "health_index",
        "rul",
    ]

    validate_dataset_columns(columns)


def test_feature_columns_are_correct():
    assert FEATURE_COLUMNS == [
        "temperature",
        "vibration",
        "pressure",
        "rpm",
        "load",
        "health_index",
    ]


def test_target_column_is_rul():
    assert TARGET_COLUMN == "rul"


def test_all_columns_are_complete():
    assert len(ALL_COLUMNS) == 9


def test_missing_column_is_rejected():
    columns = [
        "engine_id",
        "cycle",
        "temperature",
        "vibration",
        "pressure",
        "rpm",
        "load",
        "health_index",
    ]

    with pytest.raises(ValueError):
        validate_dataset_columns(columns)
from typing import Final


# ---------------------------------------------------------
# M5 - Unified Dataset Contract
# ---------------------------------------------------------

METADATA_COLUMNS: Final[list[str]] = [
    "engine_id",
    "cycle",
]

FEATURE_COLUMNS: Final[list[str]] = [
    "temperature",
    "vibration",
    "pressure",
    "rpm",
    "load",
    "health_index",
]

TARGET_COLUMN: Final[str] = "rul"

ALL_COLUMNS: Final[list[str]] = (
    METADATA_COLUMNS
    + FEATURE_COLUMNS
    + [TARGET_COLUMN]
)


def validate_dataset_columns(columns) -> None:
    """
    Validate that a dataset follows the M5 canonical
    column contract.
    """

    actual_columns = list(columns)

    missing = [
        column
        for column in ALL_COLUMNS
        if column not in actual_columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )


def get_feature_columns() -> list[str]:
    """Return canonical model feature columns."""

    return FEATURE_COLUMNS.copy()


def get_target_column() -> str:
    """Return canonical target column."""

    return TARGET_COLUMN
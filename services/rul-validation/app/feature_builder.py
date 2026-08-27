from typing import Any, Mapping

import pandas as pd


# ---------------------------------------------------------
# M5 - Deterministic Feature Builder
# ---------------------------------------------------------

FEATURE_COLUMNS = [
    "temperature",
    "vibration",
    "pressure",
    "rpm",
    "load",
    "health_index",
]


def build_features(data: Mapping[str, Any]) -> pd.DataFrame:
    """
    Build the exact feature set expected by the M5 RUL model.

    The feature order is fixed and deterministic.
    No model prediction is performed here.
    """

    missing_features = [
        feature
        for feature in FEATURE_COLUMNS
        if feature not in data
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    # Create DataFrame with a fixed column order.
    features = pd.DataFrame(
        [
            {
                feature: data[feature]
                for feature in FEATURE_COLUMNS
            }
        ],
        columns=FEATURE_COLUMNS,
    )

    # Validate numeric values.
    for feature in FEATURE_COLUMNS:
        try:
            features[feature] = pd.to_numeric(
                features[feature]
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid numeric value for '{feature}'"
            ) from exc

    # Validate finite values.
    if not features.map(
        lambda value: pd.notna(value)
        and value not in [float("inf"), float("-inf")]
    ).all().all():
        raise ValueError(
            "Feature values must be finite numbers."
        )

    # Health index must remain within the training contract.
    health_index = features.loc[
        0,
        "health_index",
    ]

    if not 0.0 <= health_index <= 1.0:
        raise ValueError(
            "health_index must be between 0.0 and 1.0."
        )

    return features


def get_feature_names() -> list[str]:
    """
    Return the deterministic model feature order.
    """

    return FEATURE_COLUMNS.copy()
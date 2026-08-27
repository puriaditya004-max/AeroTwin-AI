from pathlib import Path

import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------
# M5 - RUL & Model Validation
# Dataset Preprocessing Pipeline
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "data" / "degradation_dataset.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

RANDOM_SEED = 42

FEATURE_COLUMNS = [
    "temperature",
    "vibration",
    "pressure",
    "rpm",
    "load",
    "health_index",
]

TARGET_COLUMN = "rul"


def load_dataset() -> pd.DataFrame:
    """Load and validate the raw degradation dataset."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "engine_id",
        "cycle",
        *FEATURE_COLUMNS,
        TARGET_COLUMN,
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    if df.empty:
        raise ValueError("Dataset is empty.")

    if df[required_columns].isnull().any().any():
        raise ValueError(
            "Dataset contains missing values."
        )

    return df


def split_by_engine(df: pd.DataFrame):
    """Split dataset by engine to prevent data leakage."""

    engines = sorted(df["engine_id"].unique())

    rng = pd.Series(engines).sample(
        frac=1,
        random_state=RANDOM_SEED,
    )

    engines = rng.tolist()

    total_engines = len(engines)

    train_count = int(total_engines * 0.70)
    validation_count = int(total_engines * 0.15)

    train_engines = engines[:train_count]

    validation_engines = engines[
        train_count:train_count + validation_count
    ]

    test_engines = engines[
        train_count + validation_count:
    ]

    train_df = df[
        df["engine_id"].isin(train_engines)
    ].copy()

    validation_df = df[
        df["engine_id"].isin(validation_engines)
    ].copy()

    test_df = df[
        df["engine_id"].isin(test_engines)
    ].copy()

    return train_df, validation_df, test_df


def preprocess_features(
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
):
    """Scale features using training data only."""

    scaler = StandardScaler()

    X_train = scaler.fit_transform(
        train_df[FEATURE_COLUMNS]
    )

    X_validation = scaler.transform(
        validation_df[FEATURE_COLUMNS]
    )

    X_test = scaler.transform(
        test_df[FEATURE_COLUMNS]
    )

    y_train = train_df[TARGET_COLUMN].values
    y_validation = validation_df[TARGET_COLUMN].values
    y_test = test_df[TARGET_COLUMN].values

    return (
        X_train,
        X_validation,
        X_test,
        y_train,
        y_validation,
        y_test,
        scaler,
    )


def save_processed_data(
    train_df,
    validation_df,
    test_df,
    X_train,
    X_validation,
    X_test,
    y_train,
    y_validation,
    y_test,
    scaler,
):
    """Save processed datasets and scaler."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save original split information
    train_df.to_csv(
        OUTPUT_DIR / "train.csv",
        index=False,
    )

    validation_df.to_csv(
        OUTPUT_DIR / "validation.csv",
        index=False,
    )

    test_df.to_csv(
        OUTPUT_DIR / "test.csv",
        index=False,
    )

    # Save scaled features + target
    train_processed = pd.DataFrame(
        X_train,
        columns=FEATURE_COLUMNS,
    )

    train_processed[TARGET_COLUMN] = y_train

    validation_processed = pd.DataFrame(
        X_validation,
        columns=FEATURE_COLUMNS,
    )

    validation_processed[TARGET_COLUMN] = y_validation

    test_processed = pd.DataFrame(
        X_test,
        columns=FEATURE_COLUMNS,
    )

    test_processed[TARGET_COLUMN] = y_test

    train_processed.to_csv(
        OUTPUT_DIR / "train_processed.csv",
        index=False,
    )

    validation_processed.to_csv(
        OUTPUT_DIR / "validation_processed.csv",
        index=False,
    )

    test_processed.to_csv(
        OUTPUT_DIR / "test_processed.csv",
        index=False,
    )

    # Save scaler for inference/API
    joblib.dump(
        scaler,
        OUTPUT_DIR / "scaler.joblib",
    )


def main():
    print("=" * 60)
    print("M5 - Dataset Preprocessing")
    print("=" * 60)

    # Load dataset
    df = load_dataset()

    print("\nRaw dataset:")
    print(f"Rows: {len(df)}")
    print(f"Engines: {df['engine_id'].nunique()}")

    # Split by engine
    train_df, validation_df, test_df = split_by_engine(df)

    print("\nEngine-wise split:")
    print(
        f"Train:      {train_df['engine_id'].nunique()} engines, "
        f"{len(train_df)} rows"
    )

    print(
        f"Validation: {validation_df['engine_id'].nunique()} engines, "
        f"{len(validation_df)} rows"
    )

    print(
        f"Test:       {test_df['engine_id'].nunique()} engines, "
        f"{len(test_df)} rows"
    )

    # Preprocess
    (
        X_train,
        X_validation,
        X_test,
        y_train,
        y_validation,
        y_test,
        scaler,
    ) = preprocess_features(
        train_df,
        validation_df,
        test_df,
    )

    # Save
    save_processed_data(
        train_df,
        validation_df,
        test_df,
        X_train,
        X_validation,
        X_test,
        y_train,
        y_validation,
        y_test,
        scaler,
    )

    print("\nFeature columns:")
    print(FEATURE_COLUMNS)

    print("\nTarget:")
    print(TARGET_COLUMN)

    print("\nProcessed data saved to:")
    print(OUTPUT_DIR)

    print("\nScaler saved:")
    print(OUTPUT_DIR / "scaler.joblib")

    print("\n" + "=" * 60)
    print("Preprocessing completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
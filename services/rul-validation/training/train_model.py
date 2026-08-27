from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ---------------------------------------------------------
# M5 - RUL & Model Validation
# XGBoost RUL Model Training
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models"

TRAIN_FILE = DATA_DIR / "train_processed.csv"
VALIDATION_FILE = DATA_DIR / "validation_processed.csv"

MODEL_FILE = MODEL_DIR / "rul_xgboost.joblib"


FEATURE_COLUMNS = [
    "temperature",
    "vibration",
    "pressure",
    "rpm",
    "load",
    "health_index",
]

TARGET_COLUMN = "rul"


def load_data():
    """Load processed training and validation datasets."""

    if not TRAIN_FILE.exists():
        raise FileNotFoundError(
            f"Training file not found: {TRAIN_FILE}"
        )

    if not VALIDATION_FILE.exists():
        raise FileNotFoundError(
            f"Validation file not found: {VALIDATION_FILE}"
        )

    train_df = pd.read_csv(TRAIN_FILE)
    validation_df = pd.read_csv(VALIDATION_FILE)

    return train_df, validation_df


def train_model(X_train, y_train):
    """Train XGBoost regression model."""

    model = XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

    return model


def evaluate_model(model, X, y, dataset_name):
    """Evaluate model using MAE, RMSE and R2."""

    predictions = model.predict(X)

    mae = mean_absolute_error(
        y,
        predictions,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y,
            predictions,
        )
    )

    r2 = r2_score(
        y,
        predictions,
    )

    print(f"\n{dataset_name} Metrics")
    print("-" * 40)
    print(f"MAE : {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R²  : {r2:.4f}")

    return mae, rmse, r2


def main():

    print("=" * 60)
    print("M5 - XGBoost RUL Model Training")
    print("=" * 60)

    # -----------------------------------------------------
    # Load data
    # -----------------------------------------------------

    train_df, validation_df = load_data()

    print("\nTraining dataset:")
    print(f"Rows: {len(train_df)}")

    print("\nValidation dataset:")
    print(f"Rows: {len(validation_df)}")

    # -----------------------------------------------------
    # Features and target
    # -----------------------------------------------------

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]

    X_validation = validation_df[FEATURE_COLUMNS]
    y_validation = validation_df[TARGET_COLUMN]

    print("\nFeatures:")
    print(FEATURE_COLUMNS)

    print("\nTarget:")
    print(TARGET_COLUMN)

    # -----------------------------------------------------
    # Train model
    # -----------------------------------------------------

    print("\nTraining XGBoost model...")

    model = train_model(
        X_train,
        y_train,
    )

    print("Training completed.")

    # -----------------------------------------------------
    # Evaluate
    # -----------------------------------------------------

    evaluate_model(
        model,
        X_train,
        y_train,
        "Training",
    )

    evaluate_model(
        model,
        X_validation,
        y_validation,
        "Validation",
    )

    # -----------------------------------------------------
    # Save model
    # -----------------------------------------------------

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_FILE,
    )

    print("\nModel saved successfully:")
    print(MODEL_FILE)

    print("\n" + "=" * 60)
    print("M5 model training completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
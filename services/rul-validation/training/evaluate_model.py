from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ---------------------------------------------------------
# M5 - RUL & Model Validation
# Final Test Evaluation
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models"

TEST_FILE = DATA_DIR / "test_processed.csv"
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


def load_test_data():
    if not TEST_FILE.exists():
        raise FileNotFoundError(
            f"Test dataset not found: {TEST_FILE}"
        )

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    test_df = pd.read_csv(TEST_FILE)
    model = joblib.load(MODEL_FILE)

    return test_df, model


def evaluate(model, test_df):
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    predictions = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions,
        )
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    return predictions, mae, rmse, r2


def main():

    print("=" * 60)
    print("M5 - Final RUL Model Evaluation")
    print("=" * 60)

    # Load
    test_df, model = load_test_data()

    print("\nTest dataset:")
    print(f"Rows: {len(test_df)}")

    # Evaluate
    predictions, mae, rmse, r2 = evaluate(
        model,
        test_df,
    )

    print("\nFinal Test Metrics")
    print("-" * 40)

    print(f"MAE : {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R²  : {r2:.4f}")

    # Prediction statistics
    print("\nPrediction Statistics")
    print("-" * 40)

    print(
        f"Actual RUL Mean: "
        f"{test_df[TARGET_COLUMN].mean():.2f}"
    )

    print(
        f"Predicted RUL Mean: "
        f"{predictions.mean():.2f}"
    )

    print(
        f"Actual RUL Min: "
        f"{test_df[TARGET_COLUMN].min():.2f}"
    )

    print(
        f"Actual RUL Max: "
        f"{test_df[TARGET_COLUMN].max():.2f}"
    )

    # Sample predictions
    results = pd.DataFrame(
        {
            "actual_rul": test_df[TARGET_COLUMN].values,
            "predicted_rul": predictions,
        }
    )

    results["error"] = (
        results["predicted_rul"]
        - results["actual_rul"]
    )

    print("\nSample Predictions")
    print("-" * 40)

    print(
        results.head(10).to_string(
            index=False
        )
    )

    # Save predictions
    output_file = DATA_DIR / "test_predictions.csv"

    results.to_csv(
        output_file,
        index=False,
    )

    print("\nPrediction results saved to:")
    print(output_file)

    print("\n" + "=" * 60)
    print("Final test evaluation completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
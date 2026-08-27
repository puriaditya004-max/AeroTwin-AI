
from pathlib import Path

import joblib
import mlflow
import mlflow.xgboost
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# =========================================================
# M5 - MLflow Experiment Tracking + Model Registry
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

TRAINING_DIR = BASE_DIR

DATA_DIR = TRAINING_DIR / "data" / "processed"

MODEL_PATH = (
    TRAINING_DIR
    / "models"
    / "rul_xgboost.joblib"
)

TRAIN_PATH = DATA_DIR / "train_processed.csv"
VALIDATION_PATH = DATA_DIR / "validation_processed.csv"

MLFLOW_DB = TRAINING_DIR / "mlflow.db"

TRACKING_URI = f"sqlite:///{MLFLOW_DB.as_posix()}"

EXPERIMENT_NAME = "AeroTwin-M5-RUL"

REGISTERED_MODEL_NAME = "AeroTwin-M5-RUL-XGBoost"

FEATURE_COLUMNS = [
    "temperature",
    "vibration",
    "pressure",
    "rpm",
    "load",
    "health_index",
]

TARGET_COLUMN = "rul"


# =========================================================
# Calculate Metrics
# =========================================================

def calculate_metrics(model, data_path):
    """
    Load processed dataset and calculate
    model evaluation metrics.
    """

    import pandas as pd

    df = pd.read_csv(data_path)

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    predictions = model.predict(X)

    mae = mean_absolute_error(y, predictions)

    rmse = mean_squared_error(
        y,
        predictions,
    ) ** 0.5

    r2 = r2_score(
        y,
        predictions,
    )

    return mae, rmse, r2


# =========================================================
# Main
# =========================================================

def main():

    print("=" * 60)
    print("M5 - MLflow Tracking + Model Registry")
    print("=" * 60)

    # -----------------------------------------------------
    # Validate files
    # -----------------------------------------------------

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
        )

    if not TRAIN_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found:\n{TRAIN_PATH}"
        )

    if not VALIDATION_PATH.exists():
        raise FileNotFoundError(
            f"Validation dataset not found:\n{VALIDATION_PATH}"
        )

    # -----------------------------------------------------
    # Load trained model
    # -----------------------------------------------------

    model = joblib.load(MODEL_PATH)

    print("\nLoaded model:")
    print(MODEL_PATH)

    # -----------------------------------------------------
    # Configure MLflow
    # -----------------------------------------------------

    mlflow.set_tracking_uri(TRACKING_URI)

    print("\nMLflow Tracking URI:")
    print(TRACKING_URI)

    print("\nActive Tracking URI:")
    print(mlflow.get_tracking_uri())

    # -----------------------------------------------------
    # Create / select experiment
    # -----------------------------------------------------

    mlflow.set_experiment(
        EXPERIMENT_NAME
    )

    # -----------------------------------------------------
    # Calculate metrics
    # -----------------------------------------------------

    train_mae, train_rmse, train_r2 = calculate_metrics(
        model,
        TRAIN_PATH,
    )

    val_mae, val_rmse, val_r2 = calculate_metrics(
        model,
        VALIDATION_PATH,
    )

    print("\nTraining Metrics")
    print("-" * 40)
    print(f"MAE : {train_mae:.4f}")
    print(f"RMSE: {train_rmse:.4f}")
    print(f"R2  : {train_r2:.4f}")

    print("\nValidation Metrics")
    print("-" * 40)
    print(f"MAE : {val_mae:.4f}")
    print(f"RMSE: {val_rmse:.4f}")
    print(f"R2  : {val_r2:.4f}")

    # -----------------------------------------------------
    # Start MLflow Run
    # -----------------------------------------------------

    with mlflow.start_run(
        run_name="rul-xgboost-v1"
    ):

        # -------------------------------------------------
        # Log Parameters
        # -------------------------------------------------

        mlflow.log_param(
            "model_type",
            "XGBoost",
        )

        mlflow.log_param(
            "task",
            "Remaining Useful Life prediction",
        )

        mlflow.log_param(
            "target",
            TARGET_COLUMN,
        )

        mlflow.log_param(
            "feature_count",
            len(FEATURE_COLUMNS),
        )

        mlflow.log_param(
            "model_file",
            MODEL_PATH.name,
        )

        mlflow.log_param(
            "model_version",
            "1.0.0",
        )

        # -------------------------------------------------
        # Log Training Metrics
        # -------------------------------------------------

        mlflow.log_metric(
            "train_mae",
            train_mae,
        )

        mlflow.log_metric(
            "train_rmse",
            train_rmse,
        )

        mlflow.log_metric(
            "train_r2",
            train_r2,
        )

        # -------------------------------------------------
        # Log Validation Metrics
        # -------------------------------------------------

        mlflow.log_metric(
            "validation_mae",
            val_mae,
        )

        mlflow.log_metric(
            "validation_rmse",
            val_rmse,
        )

        mlflow.log_metric(
            "validation_r2",
            val_r2,
        )

        # -------------------------------------------------
        # Tags
        # -------------------------------------------------

        mlflow.set_tag(
            "features",
            ",".join(FEATURE_COLUMNS),
        )

        mlflow.set_tag(
            "service",
            "AeroTwin-AI-M5",
        )

        mlflow.set_tag(
            "framework",
            "XGBoost",
        )

        mlflow.set_tag(
            "model_status",
            "VALIDATED",
        )

        # -------------------------------------------------
        # Log Existing Model Artifact
        # -------------------------------------------------

        print("\nLogging model artifact...")

        mlflow.log_artifact(
            str(MODEL_PATH),
            artifact_path="model",
        )

        print(
            "Model artifact logged successfully."
        )

        # -------------------------------------------------
        # Register Model
        # -------------------------------------------------

        print("\nRegistering model in MLflow Model Registry...")

        model_info = mlflow.xgboost.log_model(
            xgb_model=model,
            artifact_path="registered_model",
            registered_model_name=REGISTERED_MODEL_NAME,
        )

        print(
            "Model registered successfully."
        )

        print("\nRegistered Model Name:")
        print(REGISTERED_MODEL_NAME)

        # -------------------------------------------------
        # Model URI
        # -------------------------------------------------

        print("\nModel URI:")
        print(model_info.model_uri)

        # -------------------------------------------------
        # Run information
        # -------------------------------------------------

        run = mlflow.active_run()

        if run is not None:

            print("\nMLflow Run ID:")
            print(run.info.run_id)

            print("\nArtifact URI:")
            print(run.info.artifact_uri)

    print("\n" + "=" * 60)
    print("MLflow tracking + model registration completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

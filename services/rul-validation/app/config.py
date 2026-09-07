from pathlib import Path


# =========================================================
# M5 Service Configuration
# =========================================================

APP_DIR = Path(__file__).resolve().parent

SERVICE_DIR = APP_DIR.parent

TRAINING_DIR = SERVICE_DIR / "training"


# =========================================================
# Local Model
# =========================================================

MODEL_FILE = (
    TRAINING_DIR
    / "models"
    / "rul_xgboost.joblib"
)


# =========================================================
# Scaler
# =========================================================

SCALER_FILE = (
    TRAINING_DIR
    / "data"
    / "processed"
    / "scaler.joblib"
)


# =========================================================
# MLflow
# =========================================================

MLFLOW_DB = TRAINING_DIR / "mlflow.db"

MLFLOW_TRACKING_URI = (
    f"sqlite:///{MLFLOW_DB.as_posix()}"
)


# Registered model name
MLFLOW_MODEL_NAME = (
    "AeroTwin-M5-RUL-XGBoost"
)


import os

MLFLOW_MODEL_VERSION = os.getenv(
    "MLFLOW_MODEL_VERSION",
    "4",
)


# =========================================================
# Model Metadata
# =========================================================

MODEL_NAME = "rul_xgboost"

MODEL_VERSION = "1.0.0"

MODEL_FRAMEWORK = "xgboost"

MODEL_TASK = "remaining_useful_life"


# =========================================================
# Features
# =========================================================

FEATURE_COLUMNS = [
    "temperature",
    "vibration",
    "pressure",
    "rpm",
    "load",
    "health_index",
]


# =========================================================
# Validation
# =========================================================

MIN_RUL = 0.0

MAX_RUL = 300.0


# =========================================================
# Service
# =========================================================

SERVICE_NAME = (
    "AeroTwin-AI M5 RUL Validation"
)

API_VERSION = "1.0.0"
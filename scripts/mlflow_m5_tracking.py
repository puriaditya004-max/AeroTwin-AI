import os
import pandas as pd
import mlflow
import mlflow.xgboost
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# --------------------------------
# 1. Load M5 processed data
# --------------------------------

train_file = "data/processed/m5_train.csv"
test_file = "data/processed/m5_test.csv"

train_df = pd.read_csv(train_file)
test_df = pd.read_csv(test_file)


# --------------------------------
# 2. Features and target
# --------------------------------

features = [
    "cycle",
    "health_score",
    "fault_confidence",
    "anomaly_score",
    "temperature",
    "oil_pressure",
    "vibration"
]

target = "rul_target"

X_train = train_df[features]
y_train = train_df[target]

X_test = test_df[features]
y_test = test_df[target]


# --------------------------------
# 3. Model parameters
# --------------------------------

params = {
    "n_estimators": 100,
    "max_depth": 3,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "reg:squarederror",
    "random_state": 42
}


# --------------------------------
# 4. MLflow experiment
# --------------------------------

mlflow.set_tracking_uri("sqlite:///mlflow.db")

mlflow.set_experiment("AeroTwin-AI-M5-RUL")


with mlflow.start_run(run_name="M5-XGBoost-RUL"):

    # Create model
    model = XGBRegressor(**params)

    # Train
    print("Training M5 XGBoost model...")
    model.fit(X_train, y_train)

    # Predict
    y_pred = model.predict(X_test)

    # Metrics
    mae = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred) ** 0.5
    r2 = r2_score(y_test, y_pred)

    # Log parameters
    mlflow.log_params(params)

    # Log metrics
    mlflow.log_metric("MAE", mae)
    mlflow.log_metric("RMSE", rmse)
    mlflow.log_metric("R2", r2)

    # Log model
    mlflow.xgboost.log_model(
        model,
        name="m5_rul_xgboost_model"
    )

    print("\nM5 MLflow Run Completed")
    print("=" * 40)
    print(f"MAE  : {mae:.2f}")
    print(f"RMSE : {rmse:.2f}")
    print(f"R2   : {r2:.4f}")
    print("\nExperiment: AeroTwin-AI-M5-RUL")
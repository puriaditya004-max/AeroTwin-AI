import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# --------------------------------
# 1. Load test dataset
# --------------------------------

test_file = "data/processed/m5_test.csv"

test_df = pd.read_csv(test_file)


# --------------------------------
# 2. Load trained model
# --------------------------------

model_file = "models/m5_rul_xgboost.pkl"

model = joblib.load(model_file)


# --------------------------------
# 3. Features and target
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


X_test = test_df[features]
y_test = test_df[target]


# --------------------------------
# 4. Predict RUL
# --------------------------------

y_pred = model.predict(X_test)


# --------------------------------
# 5. Evaluation metrics
# --------------------------------

mae = mean_absolute_error(y_test, y_pred)
rmse = mean_squared_error(y_test, y_pred) ** 0.5
r2 = r2_score(y_test, y_pred)


print("\nM5 RUL MODEL EVALUATION")
print("=" * 40)

print(f"MAE  : {mae:.2f}")
print(f"RMSE : {rmse:.2f}")
print(f"R2   : {r2:.4f}")


# --------------------------------
# 6. Actual vs Predicted
# --------------------------------

results = pd.DataFrame({
    "Actual_RUL": y_test.values,
    "Predicted_RUL": y_pred.round(2),
    "Absolute_Error": abs(
        y_test.values - y_pred
    ).round(2)
})


print("\nActual vs Predicted RUL")
print("=" * 40)

print(results.to_string(index=False))
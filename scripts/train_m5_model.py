import os
import pandas as pd
import joblib

from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# --------------------------------
# 1. Load processed data
# --------------------------------

train_file = "data/processed/m5_train.csv"
test_file = "data/processed/m5_test.csv"

train_df = pd.read_csv(train_file)
test_df = pd.read_csv(test_file)

print("Training data:", train_df.shape)
print("Testing data :", test_df.shape)


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
# 3. Create XGBoost model
# --------------------------------

model = XGBRegressor(
    n_estimators=100,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42
)


# --------------------------------
# 4. Train model
# --------------------------------

print("\nTraining M5 XGBoost model...")

model.fit(X_train, y_train)

print("Training completed!")


# --------------------------------
# 5. Predictions
# --------------------------------

y_pred = model.predict(X_test)


# --------------------------------
# 6. Evaluation
# --------------------------------

mae = mean_absolute_error(y_test, y_pred)
rmse = mean_squared_error(y_test, y_pred) ** 0.5
r2 = r2_score(y_test, y_pred)


print("\nM5 Model Performance")
print("-----------------------------")
print(f"MAE  : {mae:.2f}")
print(f"RMSE : {rmse:.2f}")
print(f"R2   : {r2:.4f}")


# --------------------------------
# 7. Save model
# --------------------------------

model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

model_file = "models/m5_rul_xgboost.pkl"

joblib.dump(model, model_file)

print("\nModel saved successfully!")
print(f"Path: {model_file}")
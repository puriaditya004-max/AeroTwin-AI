import pandas as pd
import joblib


# --------------------------------
# 1. Load trained M5 model
# --------------------------------

model_file = "models/m5_rul_xgboost.pkl"

model = joblib.load(model_file)


# --------------------------------
# 2. New engine sensor data
# --------------------------------

new_data = pd.DataFrame([{
    "cycle": 600,
    "health_score": 44,
    "fault_confidence": 0.65,
    "anomaly_score": 0.65,
    "temperature": 95,
    "oil_pressure": 52,
    "vibration": 4.0
}])


# --------------------------------
# 3. Predict RUL
# --------------------------------

predicted_rul = model.predict(new_data)[0]


# --------------------------------
# 4. Determine Risk Level
# --------------------------------

if predicted_rul <= 200:
    risk_level = "HIGH"
    recommendation = "Immediate Maintenance Required"

elif predicted_rul <= 400:
    risk_level = "MEDIUM"
    recommendation = "Schedule Maintenance"

else:
    risk_level = "LOW"
    recommendation = "Continue Monitoring"


# --------------------------------
# 5. Display Prediction
# --------------------------------

print("\nAEROTWIN-AI M5 RUL PREDICTION")
print("=" * 50)

print("\nInput Sensor Data")
print("-" * 50)

print(new_data.to_string(index=False))

print("\nPrediction Result")
print("-" * 50)

print(f"Predicted RUL          : {predicted_rul:.2f} cycles")
print(f"Risk Level             : {risk_level}")
print(f"Maintenance Action     : {recommendation}")

print("=" * 50)
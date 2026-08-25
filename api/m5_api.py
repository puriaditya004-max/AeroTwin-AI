from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import joblib


# --------------------------------
# 1. Create FastAPI application
# --------------------------------

app = FastAPI(
    title="AeroTwin-AI M5 RUL API",
    description="Predictive maintenance API for UAV engine RUL",
    version="1.0.0"
)


# --------------------------------
# 2. Load trained M5 model
# --------------------------------

MODEL_PATH = "models/m5_rul_xgboost.pkl"

model = joblib.load(MODEL_PATH)


# --------------------------------
# 3. Input data schema
# --------------------------------

class SensorData(BaseModel):

    cycle: float
    health_score: float
    fault_confidence: float
    anomaly_score: float
    temperature: float
    oil_pressure: float
    vibration: float


# --------------------------------
# 4. Health check endpoint
# --------------------------------

@app.get("/")
def root():

    return {
        "project": "AeroTwin-AI",
        "module": "M5 RUL Prediction",
        "status": "API is running"
    }


# --------------------------------
# 5. RUL prediction endpoint
# --------------------------------

@app.post("/predict")
def predict_rul(data: SensorData):

    input_data = pd.DataFrame([{
        "cycle": data.cycle,
        "health_score": data.health_score,
        "fault_confidence": data.fault_confidence,
        "anomaly_score": data.anomaly_score,
        "temperature": data.temperature,
        "oil_pressure": data.oil_pressure,
        "vibration": data.vibration
    }])

    # Predict RUL
    predicted_rul = float(model.predict(input_data)[0])


    # Determine risk
    if predicted_rul <= 200:

        risk_level = "HIGH"
        recommendation = "Immediate Maintenance Required"

    elif predicted_rul <= 400:

        risk_level = "MEDIUM"
        recommendation = "Schedule Maintenance"

    else:

        risk_level = "LOW"
        recommendation = "Continue Monitoring"


    return {
        "predicted_rul": round(predicted_rul, 2),
        "unit": "cycles",
        "risk_level": risk_level,
        "maintenance_recommendation": recommendation
    }
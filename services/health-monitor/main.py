import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException

# --- INCOMING DATA CONTRACT (From Module 2) ---
class TwinStateInput(BaseModel):
    engineId: str
    missionId: str
    stateTime: str
    load: float
    derivedFeatures: Dict[str, float]
    margins: Dict[str, float]
    stateQuality: str

# --- OUTGOING DATA CONTRACT (Module 3 Output) ---
class HealthSnapshot(BaseModel):
    engineId: str
    missionId: str
    timestamp: str
    healthScore: float  # Range: 0 to 100
    subScores: Dict[str, float]
    violatedRules: List[str]
    reasonCodes: List[str]
    ruleVersion: str = "v1.0.0"

# --- HEALTH ENGINE LOGIC ---
class PhysicsHealthEngine:
    def __init__(self):
        # Operational limits and physics threshold guardrails
        self.SAFE_TEMP_LIMIT = 200.0       # Max safe Temp (°C)
        self.CRITICAL_TEMP_LIMIT = 230.0   # Dangerous Temp (°C)
        self.MIN_PRESSURE_LIMIT = 2.0      # Min safe Pressure (bar)
        self.MAX_VIBRATION_RMS = 0.08      # Max safe Vibration

    def evaluate_health(self, state: TwinStateInput) -> HealthSnapshot:
        rpm = state.derivedFeatures.get("rpm", 0.0)
        vibration = state.derivedFeatures.get("vibration_rms", 0.0)
        
        # Margins calculated from M2
        temp_margin = state.margins.get("temperature_margin_c", 50.0)
        pressure_margin = state.margins.get("pressure_margin_bar", 2.0)
        
        # Estimate raw metrics back from margins
        current_temp = 250.0 - temp_margin
        current_pressure = pressure_margin + 2.5

        violated_rules = []
        reason_codes = []

        # 1. Temperature Sub-score (Max 30 pts)
        temp_score = 30.0
        if current_temp > self.CRITICAL_TEMP_LIMIT:
            temp_score = 5.0
            violated_rules.append("RULE_TEMP_CRITICAL")
            reason_codes.append("CRITICAL_ENGINE_OVERHEATING")
        elif current_temp > self.SAFE_TEMP_LIMIT:
            temp_score = 18.0
            violated_rules.append("RULE_TEMP_WARN")
            reason_codes.append("ELEVATED_TEMPERATURE")

        # 2. Oil Pressure Sub-score (Max 30 pts)
        pressure_score = 30.0
        if current_pressure < self.MIN_PRESSURE_LIMIT:
            pressure_score = 5.0
            violated_rules.append("RULE_PRESSURE_LOW")
            reason_codes.append("LOW_OIL_PRESSURE_WARNING")

        # 3. Vibration Sub-score (Max 25 pts)
        vibration_score = 25.0
        if vibration > self.MAX_VIBRATION_RMS:
            vibration_score = 10.0
            violated_rules.append("RULE_VIBRATION_EXCEEDED")
            reason_codes.append("HIGH_ENGINE_VIBRATION")

        # 4. State Data Quality Penalty (Max 15 pts)
        quality_score = 15.0
        if state.stateQuality != "VALID":
            quality_score = 5.0
            reason_codes.append("SENSOR_DATA_DEGRADED")

        # Total Composite Health Score (0 - 100)
        total_health = float(np.clip(temp_score + pressure_score + vibration_score + quality_score, 0.0, 100.0))

        if total_health == 100.0:
            reason_codes.append("ALL_SYSTEMS_NOMINAL")

        return HealthSnapshot(
            engineId=state.engineId,
            missionId=state.missionId,
            timestamp=state.stateTime,
            healthScore=round(total_health, 1),
            subScores={
                "temperature": round(temp_score, 1),
                "pressure": round(pressure_score, 1),
                "vibration": round(vibration_score, 1),
                "dataQuality": round(quality_score, 1)
            },
            violatedRules=violated_rules,
            reasonCodes=reason_codes
        )

# --- FASTAPI SERVICE IMPLEMENTATION ---
app = FastAPI(
    title="AeroTwin AI - Module 3 Health Rules Service",
    version="1.0.0",
    description="Physics-based engine health evaluation and rule engine."
)

engine = PhysicsHealthEngine()

@app.post("/evaluate", response_model=HealthSnapshot)
async def evaluate_engine_health(twin_state: TwinStateInput):
    """Processes TwinState from M2 and outputs a HealthSnapshot."""
    return engine.evaluate_health(twin_state)

@app.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {"status": "HEALTHY", "service": "health-rules-service", "module": "M3"}
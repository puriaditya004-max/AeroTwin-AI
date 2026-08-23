# M4 — Fault Prediction & Explainable AI

**Owner:** TBD | **Workload:** 18% (highest technical difficulty) | **Commitment:** Core MVP
**Branch:** `feature/fault-prediction`

## Problem Owned
Detect abnormal behavior, classify a likely fault, and explain which signals influenced the prediction.

## Stack
Python 3.12, Pandas, scikit-learn, XGBoost, SHAP, MLflow, Joblib, Pytest

## Implementation Checklist
- [ ] Build feature pipeline from rolling twin-state windows — **no target leakage**
- [ ] Train Isolation Forest or compact baseline anomaly detector
- [ ] Train small classifier: normal / overheating / oil-pressure / vibration / sensor-fault
- [ ] Measure precision, recall, F1, confusion matrix, detection delay
- [ ] Generate SHAP or transparent feature-contribution explanations
- [ ] Version dataset, features, thresholds, model artifacts

## Required Outputs
- Feature pipeline
- Anomaly model
- Fault classifier
- `FaultPrediction` contract

## Acceptance Tests
- Fixed test split
- Confusion matrix
- Detection delay
- Explanation sanity check

## Contracts
- **Consumes:** `TwinState` windows from M2
- **Produces:** `FaultPrediction`: `faultType, confidence, anomalyScore, contributors, version` → **consumed by M5/M6**

## Judge Explanation Responsibility
Dataset creation, feature choices, false alarms, model metrics, why the result is probabilistic rather than guaranteed.

## Handoff
Consumes M2 state windows. Hands `FaultPrediction` + model metadata to M5 and M6.

## ⚠️ Note
This is the most technically demanding module (ML modeling + explainability). Select for genuine ML competence — a weak candidate here compromises the entire fault→RUL→advisory chain.

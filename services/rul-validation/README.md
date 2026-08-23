# M5 — RUL & Model Validation

**Owner:** TBD | **Workload:** 16% | **Commitment:** Experimental
**Branch:** `feature/rul-validation`

## Problem Owned
Estimate an experimental remaining-life proxy with uncertainty, and validate the complete intelligence pipeline.

## Stack
Python 3.12, Pandas, scikit-learn, XGBoost, MLflow, Joblib, Pytest

## Implementation Checklist
- [ ] Create monotonic degradation targets for documented synthetic scenarios
- [ ] Train regression baseline; compare against simple rule-based RUL proxy
- [ ] Output estimated cycles, lower/upper confidence range, trend
- [ ] Measure MAE/RMSE; verify degradation never incorrectly improves RUL
- [ ] Run cross-module scenario validation using health + fault outputs
- [ ] If evidence is weak: label RUL experimental, strengthen validation — do NOT overstate accuracy

## Required Outputs
- RUL baseline
- `RulEstimate` contract
- Validation report
- Model registry entries

## Acceptance Tests
- MAE/RMSE
- Monotonic trend
- Uncertainty output
- Scenario backtest

## Contracts
- **Consumes:** `HealthSnapshot` (M3), `FaultPrediction` (M4)
- **Produces:** `RulEstimate`: `cycles, lowerBound, upperBound, trend, version` → **consumed by M6**

## Judge Explanation Responsibility
Difference between a demonstrator RUL proxy and field-validated remaining life, including public-data domain limitations.

## Handoff
Consumes `HealthSnapshot` and `FaultPrediction`. Supplies `RulEstimate` + validation results to M6.

## ⚠️ Note
Experimental commitment — if quality is weak, strengthen validation and metrics honesty instead of making unsupported accuracy claims.

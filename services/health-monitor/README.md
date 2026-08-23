# M3 — Health Monitoring & Physics Rules

**Owner:** TBD | **Workload:** 15% | **Commitment:** Core MVP
**Branch:** `feature/health-monitoring`

## Problem Owned
Convert twin state into an explainable engine Health Index using operating envelopes and physics-inspired guardrails.

## Stack
Python 3.12, NumPy, Pandas, SciPy, Pydantic, rule configuration, Pytest

## Implementation Checklist
- [ ] Define mentor-reviewed sensor limits, rate-of-change limits, mission-aware thresholds
- [ ] Calculate temperature, pressure, vibration, load health sub-scores
- [ ] Combine sub-scores into Health Index (0–100) with reason codes
- [ ] Detect impossible combinations; separate sensor-quality issues from engine-health issues
- [ ] Store rule version, violated rules, degradation trend in `HealthSnapshot`
- [ ] Document assumptions; keep all thresholds configurable

## Required Outputs
- Health rules
- `HealthSnapshot` contract
- Reason-code catalog
- Assumption report

## Acceptance Tests
- Boundary values
- Trend degradation
- Quality-vs-health separation
- Rule version trace

## Contracts
- **Consumes:** `TwinState` from M2
- **Produces:** `HealthSnapshot`: `healthScore, trend, violatedRules, reasonCodes` → **consumed by M5/M6**

## Judge Explanation Responsibility
Each health-score contribution, domain assumptions, why the system remains an advisory demonstrator.

## Handoff
Consumes M2 `TwinState`. Supplies `HealthSnapshot` to M5 and M6. Coordinates domain assumptions with faculty mentor.

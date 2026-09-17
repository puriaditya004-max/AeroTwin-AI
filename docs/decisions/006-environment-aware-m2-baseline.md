# ADR 006: Add additive environment-aware expected values to M2

## Decision

M2 now derives expected oil-temperature, coolant-temperature, oil-pressure,
and vibration values from the telemetry context already provided by M1:
altitude, ambient temperature, RPM, throttle, and fuel flow. It exposes the
expected values and actual-minus-expected deviations as optional additive fields
on `TwinState.derivedFeatures`.

## Why

A fixed threshold can raise a false alert when the same measured value is
normal for a high-load or hot-environment condition. M4 needs a stable
actual-versus-expected boundary before its classifier can be upgraded and
retrained for environment-aware inference.

## Safety boundary

The baseline coefficients are documented SIH demonstrator heuristics. They are
not certified engine physics, real-engine calibration, or airworthiness limits.
M4 continues to use its validated current feature set until a separately tested
model/artifact upgrade consumes these new deviation fields.

M4's decision-fusion safety gate may use the new deviations to corroborate or
suppress an existing classifier result. It does not add the fields to the
current model feature vector, so the committed M4 artifacts remain compatible.

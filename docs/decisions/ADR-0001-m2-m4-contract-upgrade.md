# ADR-0001 - M2/M4 Contract Upgrade

## Status

Accepted for hackathon demonstrator.

## Context

AeroTwin AI modules M2 and M4 need richer piston-engine state features while
remaining compatible with existing v1 telemetry/state payloads used by M1, M3,
M5, M6, and the Operator HMI.

## Decision

Use an additive, backward-compatible contract upgrade:

- Existing v1 required fields remain unchanged.
- New fields are optional and may be omitted by v1 producers.
- `schemaVersion`, `frameId`, `ingestTimestamp`, sensor quality metadata, and
  cylinder/electrical/injection measurements are optional on `TelemetryFrame`.
- M2 emits extended `derivedFeatures` when optional sensors are available.
- Missing optional sensors degrade confidence and add reason codes, but never
  crash M2 or invent readings.
- M2 uses `configs/engine_profile.sih-demo.yaml` for demonstrator limits and
  feature calculations. These values are not certified DRDO engine limits.

## Compatibility

Consumers that only read the original `TwinState` fields continue to work:

- `engineId`
- `missionId`
- `correlationId`
- `stateTime`
- `producerVersion`
- `load`
- `margins`
- `derivedFeatures.rollingMeanRpm`
- `derivedFeatures.rollingStdVibration`
- `derivedFeatures.rateOfChangeOilTempCPerMin`
- `derivedFeatures.sampleWindowSeconds`
- `stateQuality`
- `syncLagMs`

## Consequences

M2 can support v2 SIH/DRDO-relevant telemetry without blocking existing v1
modules. M4 can later consume the richer feature set while maintaining a safe
fallback for stale/degraded states.

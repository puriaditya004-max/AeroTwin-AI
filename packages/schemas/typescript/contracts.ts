/**
 * AeroTwin AI - Shared contract schemas (Zod)
 *
 * Canonical source of truth is /packages/schemas/json-schema/*.schema.json.
 * These Zod schemas mirror those definitions for use in Control API (M6)
 * and the Operator HMI. Do not edit a contract here without updating the
 * matching JSON Schema and writing a short ADR in /docs/decisions/.
 *
 * Usage:
 *   import { TelemetryFrameSchema, type TelemetryFrame } from "./contracts";
 *   const frame = TelemetryFrameSchema.parse(rawPayload);
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// TelemetryFrame  (Producer: M1 -> Consumer: M2)
// ---------------------------------------------------------------------------

export const QualityFlagSchema = z.enum([
  "OK",
  "DEGRADED",
  "DROPOUT",
  "DUPLICATE",
  "OUT_OF_ORDER",
]);

export const SensorQualityCodeSchema = z.enum([
  "OK",
  "MISSING",
  "STALE",
  "OUT_OF_RANGE",
  "DEGRADED",
]);

export const SensorQualitySchema = z.object({
  status: SensorQualityCodeSchema,
  reason: z.string().optional(),
});

export const SensorsSchema = z.object({
  rpm: z.number().min(0).max(4000),
  oilPressureKpa: z.number().min(0).max(1000),
  oilTempC: z.number().min(-40).max(200),
  coolantTempC: z.number().min(-40).max(200),
  vibrationMmS: z.number().min(0).max(50),
  fuelFlowLph: z.number().min(0).max(100),
  throttlePct: z.number().min(0).max(100),
  altitudeM: z.number().min(0).max(12000),
  ambientTempC: z.number().min(-60).max(60),
  ambientPressureKpa: z.number().min(10).max(110),
  chtCylindersC: z.array(z.number()).optional(),
  egtCylindersC: z.array(z.number()).optional(),
  alternatorVoltageV: z.number().min(0).max(40).optional(),
  alternatorCurrentA: z.number().min(-50).max(150).optional(),
  batteryVoltageV: z.number().min(0).max(40).optional(),
  injectionTimingDeg: z.number().min(-60).max(60).optional(),
  sensorQuality: z.record(z.string(), SensorQualitySchema).optional(),
}).passthrough();

export const TelemetryFrameSchema = z.object({
  schemaVersion: z.string().optional(),
  engineId: z.string(),
  missionId: z.string(),
  frameId: z.string().optional(),
  correlationId: z.string(),
  timestamp: z.string().datetime(),
  ingestTimestamp: z.string().datetime().optional(),
  producerVersion: z.string(),
  sensors: SensorsSchema,
  qualityFlag: QualityFlagSchema,
  scenarioId: z.string().optional(),
}).passthrough();

export type TelemetryFrame = z.infer<typeof TelemetryFrameSchema>;

// ---------------------------------------------------------------------------
// TwinState  (Producer: M2 -> Consumers: M3, M4, M5)
// ---------------------------------------------------------------------------

export const StateQualitySchema = z.enum(["GOOD", "STALE", "DEGRADED"]);

export const MarginsSchema = z.object({
  tempMarginC: z.number(),
  pressureMarginKpa: z.number(),
  vibrationMarginMmS: z.number(),
});

export const DerivedFeaturesSchema = z.object({
  rollingMeanRpm: z.number(),
  rollingStdVibration: z.number(),
  rateOfChangeOilTempCPerMin: z.number(),
  sampleWindowSeconds: z.number().min(0),
  featureVersion: z.string().optional(),
  chtMaxC: z.number().optional(),
  chtMeanC: z.number().optional(),
  chtSpreadC: z.number().optional(),
  chtSlopeCPerMin: z.number().optional(),
  egtMaxC: z.number().optional(),
  egtMeanC: z.number().optional(),
  egtSpreadC: z.number().optional(),
  egtSlopeCPerMin: z.number().optional(),
  oilPressureDeviationKpa: z.number().optional(),
  fuelFlowDeviationLph: z.number().optional(),
  injectionTimingDeviationDeg: z.number().optional(),
  alternatorVoltageMarginV: z.number().optional(),
  batteryVoltageMarginV: z.number().optional(),
  vibrationRollingMeanMmS: z.number().optional(),
  vibrationSlopeMmSPerMin: z.number().optional(),
  vibrationPeakMmS: z.number().optional(),
  missingSensorRatio: z.number().min(0).max(1).optional(),
  invalidSensorRatio: z.number().min(0).max(1).optional(),
  stateConfidence: z.number().min(0).max(1).optional(),
  reasonCodes: z.array(z.string()).optional(),
}).passthrough();

export const TwinStateSchema = z.object({
  schemaVersion: z.string().optional(),
  engineId: z.string(),
  missionId: z.string(),
  correlationId: z.string(),
  stateTime: z.string().datetime(),
  producerVersion: z.string(),
  load: z.number().min(0).max(100),
  margins: MarginsSchema,
  derivedFeatures: DerivedFeaturesSchema,
  stateQuality: StateQualitySchema,
  syncLagMs: z.number().min(0).optional(),
}).passthrough();

export type TwinState = z.infer<typeof TwinStateSchema>;

// ---------------------------------------------------------------------------
// HealthSnapshot  (Producer: M3 -> Consumers: M5, M6)
// ---------------------------------------------------------------------------

export const TrendSchema = z.enum(["IMPROVING", "STABLE", "DEGRADING"]);

export const SubScoresSchema = z.object({
  temperature: z.number().min(0).max(100).optional(),
  pressure: z.number().min(0).max(100).optional(),
  vibration: z.number().min(0).max(100).optional(),
  load: z.number().min(0).max(100).optional(),
});

export const HealthSnapshotSchema = z.object({
  engineId: z.string(),
  missionId: z.string(),
  correlationId: z.string(),
  snapshotTime: z.string().datetime(),
  producerVersion: z.string(),
  healthScore: z.number().min(0).max(100),
  trend: TrendSchema,
  subScores: SubScoresSchema.optional(),
  violatedRules: z.array(z.string()),
  reasonCodes: z.array(z.string()),
  ruleVersion: z.string(),
  dataQualityIssue: z.boolean().default(false),
});

export type HealthSnapshot = z.infer<typeof HealthSnapshotSchema>;

// ---------------------------------------------------------------------------
// FaultPrediction  (Producer: M4 -> Consumers: M5, M6)
// ---------------------------------------------------------------------------

export const FaultTypeSchema = z.enum([
  "NONE",
  "OVERHEATING",
  "OIL_PRESSURE_DEGRADATION",
  "VIBRATION_MISFIRE",
  "SENSOR_FAULT",
]);

export const ContributorSchema = z.object({
  feature: z.string(),
  contribution: z.number(),
});

export const FaultPredictionSchema = z.object({
  engineId: z.string(),
  missionId: z.string(),
  correlationId: z.string(),
  predictionTime: z.string().datetime(),
  producerVersion: z.string(),
  faultType: FaultTypeSchema,
  confidence: z.number().min(0).max(1),
  anomalyScore: z.number().min(0).max(1),
  contributors: z.array(ContributorSchema),
  detectionDelayMs: z.number().min(0).optional(),
});

export type FaultPrediction = z.infer<typeof FaultPredictionSchema>;

// ---------------------------------------------------------------------------
// RulEstimate  (Producer: M5 -> Consumer: M6)
// ---------------------------------------------------------------------------

export const RulBasisSchema = z.enum(["ML_REGRESSION", "RULE_BASED_PROXY"]);

export const RulEstimateSchema = z.object({
  engineId: z.string(),
  missionId: z.string(),
  correlationId: z.string(),
  estimateTime: z.string().datetime(),
  producerVersion: z.string(),
  cycles: z.number().min(0),
  lowerBound: z.number().min(0),
  upperBound: z.number().min(0),
  trend: TrendSchema,
  experimental: z.literal(true),
  basis: RulBasisSchema.optional(),
});

export type RulEstimate = z.infer<typeof RulEstimateSchema>;

// ---------------------------------------------------------------------------
// MissionAdvisory  (Producer: M6 -> Consumer: Operator HMI)
// ---------------------------------------------------------------------------

export const RiskSchema = z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]);
export const ActionSchema = z.enum(["CONTINUE", "REDUCE_LOAD", "INSPECT"]);

export const ContributingSignalsSchema = z.object({
  healthScore: z.number().optional(),
  faultType: z.string().optional(),
  faultConfidence: z.number().optional(),
  rulCycles: z.number().optional(),
});

export const SourceVersionsSchema = z.object({
  healthSnapshotVersion: z.string().optional(),
  faultPredictionVersion: z.string().optional(),
  rulEstimateVersion: z.string().optional(),
});

export const MissionAdvisorySchema = z.object({
  engineId: z.string(),
  missionId: z.string(),
  correlationId: z.string(),
  advisoryTime: z.string().datetime(),
  producerVersion: z.string(),
  risk: RiskSchema,
  action: ActionSchema,
  explanation: z.string(),
  inspectionRequired: z.boolean(),
  contributingSignals: ContributingSignalsSchema.optional(),
  sourceVersions: SourceVersionsSchema.optional(),
});

export type MissionAdvisory = z.infer<typeof MissionAdvisorySchema>;

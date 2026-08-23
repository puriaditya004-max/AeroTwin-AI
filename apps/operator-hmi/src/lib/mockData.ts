/**
 * Demo/offline data — mirrors /packages/schemas/samples/*.sample.json.
 * Used when the app runs in DEMO mode (no live Control API connection),
 * e.g. for design review or a backup demo recording.
 */

import type {
  TelemetryFrame,
  HealthSnapshot,
  FaultPrediction,
  RulEstimate,
  MissionAdvisory,
} from "../types/contracts";

export const MOCK_MISSION_ID = "MSN-OILPRESS-001";
export const MOCK_ENGINE_ID = "ENG-001";

export const mockTelemetry: TelemetryFrame = {
  engineId: MOCK_ENGINE_ID,
  missionId: MOCK_MISSION_ID,
  correlationId: "corr-8f3a1c",
  timestamp: "2026-08-22T09:14:32.500Z",
  producerVersion: "1.0.0",
  sensors: {
    rpm: 2450,
    oilPressureKpa: 210,
    oilTempC: 92,
    coolantTempC: 88,
    vibrationMmS: 3.2,
    fuelFlowLph: 18.5,
    throttlePct: 65,
    altitudeM: 3200,
    ambientTempC: 12,
    ambientPressureKpa: 68,
  },
  qualityFlag: "OK",
  scenarioId: "oil_pressure_degradation",
};

export const mockHealth: HealthSnapshot = {
  engineId: MOCK_ENGINE_ID,
  missionId: MOCK_MISSION_ID,
  correlationId: "corr-8f3a1c",
  snapshotTime: "2026-08-22T09:14:32.700Z",
  producerVersion: "1.0.0",
  healthScore: 71.5,
  trend: "DEGRADING",
  subScores: { temperature: 82, pressure: 58, vibration: 95, load: 88 },
  violatedRules: ["RULE_OIL_PRESSURE_LOW"],
  reasonCodes: ["Oil pressure trending below safe envelope over last 5 minutes"],
  ruleVersion: "rules-2026.08.1",
  dataQualityIssue: false,
};

export const mockFault: FaultPrediction = {
  engineId: MOCK_ENGINE_ID,
  missionId: MOCK_MISSION_ID,
  correlationId: "corr-8f3a1c",
  predictionTime: "2026-08-22T09:14:32.900Z",
  producerVersion: "fault-clf-1.0.0",
  faultType: "OIL_PRESSURE_DEGRADATION",
  confidence: 0.87,
  anomalyScore: 0.74,
  contributors: [
    { feature: "oilPressureKpa_rollingMean", contribution: 0.42 },
    { feature: "oilPressureKpa_rateOfChange", contribution: 0.31 },
    { feature: "oilTempC", contribution: 0.09 },
  ],
  detectionDelayMs: 4200,
};

export const mockRul: RulEstimate = {
  engineId: MOCK_ENGINE_ID,
  missionId: MOCK_MISSION_ID,
  correlationId: "corr-8f3a1c",
  estimateTime: "2026-08-22T09:14:33.000Z",
  producerVersion: "rul-reg-0.1.0",
  cycles: 340,
  lowerBound: 260,
  upperBound: 410,
  trend: "DEGRADING",
  experimental: true,
  basis: "ML_REGRESSION",
};

export const mockAdvisory: MissionAdvisory = {
  engineId: MOCK_ENGINE_ID,
  missionId: MOCK_MISSION_ID,
  correlationId: "corr-8f3a1c",
  advisoryTime: "2026-08-22T09:14:33.200Z",
  producerVersion: "control-api-1.0.0",
  risk: "HIGH",
  action: "INSPECT",
  explanation:
    "Oil pressure has degraded steadily over 5 minutes and the fault model flags oil-pressure degradation with 87% confidence. Health score fell to 71.5, driven mainly by the pressure sub-score.",
  inspectionRequired: true,
  contributingSignals: {
    healthScore: 71.5,
    faultType: "OIL_PRESSURE_DEGRADATION",
    faultConfidence: 0.87,
    rulCycles: 340,
  },
  sourceVersions: {
    healthSnapshotVersion: "rules-2026.08.1",
    faultPredictionVersion: "fault-clf-1.0.0",
    rulEstimateVersion: "rul-reg-0.1.0",
  },
};

/** Synthetic rolling history for sparklines — smooth degradation curve leading to the snapshot above. */
export function buildMockHistory(): { t: number; rpm: number; oilPressureKpa: number; oilTempC: number; vibrationMmS: number }[] {
  const points = [];
  for (let i = 0; i < 30; i++) {
    const progress = i / 29;
    points.push({
      t: i,
      rpm: 2500 - progress * 50 + Math.sin(i * 0.7) * 15,
      oilPressureKpa: 260 - progress * 50 + Math.sin(i * 0.5) * 4,
      oilTempC: 85 + progress * 7 + Math.sin(i * 0.6) * 1.5,
      vibrationMmS: 1.8 + progress * 1.4 + Math.sin(i * 0.9) * 0.2,
    });
  }
  return points;
}

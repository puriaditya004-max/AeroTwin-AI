import type { FaultPrediction, HealthSnapshot, MissionAdvisory, RulEstimate } from "../../types/contracts";

export interface AdvisoryPolicyInput {
  health: HealthSnapshot;
  fault?: FaultPrediction;
  rul?: RulEstimate;
}

export interface AdvisoryDecision {
  risk: MissionAdvisory["risk"];
  action: MissionAdvisory["action"];
  inspectionRequired: boolean;
  reasons: string[];
}

const HEALTH_CRITICAL = Number(process.env.M6_HEALTH_CRITICAL_THRESHOLD ?? 40);
const HEALTH_HIGH = Number(process.env.M6_HEALTH_HIGH_THRESHOLD ?? 60);
const HEALTH_MEDIUM = Number(process.env.M6_HEALTH_MEDIUM_THRESHOLD ?? 80);
const FAULT_CRITICAL_CONF = Number(process.env.M6_FAULT_CRITICAL_CONFIDENCE ?? 0.7);
const FAULT_HIGH_CONF = Number(process.env.M6_FAULT_HIGH_CONFIDENCE ?? 0.5);
const RUL_CRITICAL_LOWER = Number(process.env.M6_RUL_CRITICAL_LOWER_BOUND ?? 150);
const RUL_HIGH_CYCLES = Number(process.env.M6_RUL_HIGH_CYCLES ?? 300);
const RUL_MEDIUM_CYCLES = Number(process.env.M6_RUL_MEDIUM_CYCLES ?? 600);

export function deriveAdvisoryDecision(input: AdvisoryPolicyInput): AdvisoryDecision {
  const { health, fault, rul } = input;
  const reasons: string[] = [];
  const faultActive = Boolean(fault && fault.faultType !== "NONE");
  const seriousFault = Boolean(faultActive && fault!.faultType !== "SENSOR_FAULT");

  if (health.healthScore < HEALTH_CRITICAL) reasons.push("health_critical");
  if (health.dataQualityIssue) reasons.push("health_data_quality_issue");
  if (seriousFault && fault!.confidence >= FAULT_CRITICAL_CONF) reasons.push("high_confidence_fault");
  if (rul && rul.lowerBound <= RUL_CRITICAL_LOWER) reasons.push("rul_lower_bound_critical");

  if (reasons.some((r) => ["health_critical", "high_confidence_fault", "rul_lower_bound_critical"].includes(r))) {
    return { risk: "CRITICAL", action: "INSPECT", inspectionRequired: true, reasons };
  }

  if (health.healthScore < HEALTH_HIGH) reasons.push("health_high_risk");
  if (faultActive && fault!.confidence >= FAULT_HIGH_CONF) reasons.push("moderate_fault_confidence");
  if (fault && fault.anomalyScore >= 0.75) reasons.push("high_anomaly_score");
  if (rul && rul.cycles <= RUL_HIGH_CYCLES) reasons.push("rul_cycles_low");

  if (reasons.some((r) => ["health_high_risk", "moderate_fault_confidence", "high_anomaly_score", "rul_cycles_low"].includes(r))) {
    return { risk: "HIGH", action: "INSPECT", inspectionRequired: true, reasons };
  }

  if (health.healthScore < HEALTH_MEDIUM) reasons.push("health_medium_risk");
  if (health.trend === "DEGRADING") reasons.push("health_degrading");
  if (rul && (rul.cycles <= RUL_MEDIUM_CYCLES || rul.trend === "DEGRADING")) reasons.push("rul_degrading");

  if (reasons.some((r) => ["health_medium_risk", "health_degrading", "rul_degrading"].includes(r))) {
    return { risk: "MEDIUM", action: "REDUCE_LOAD", inspectionRequired: false, reasons };
  }

  return { risk: "LOW", action: "CONTINUE", inspectionRequired: false, reasons: ["nominal"] };
}

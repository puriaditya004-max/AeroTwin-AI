import type { FaultPrediction, HealthSnapshot, RulEstimate } from "../../types/contracts";
import type { AdvisoryDecision } from "./policy";

export function buildExplanation(params: {
  health: HealthSnapshot;
  fault?: FaultPrediction;
  rul?: RulEstimate;
  decision: AdvisoryDecision;
}): string {
  const { health, fault, rul, decision } = params;
  const parts: string[] = [];

  parts.push(`Health score is ${health.healthScore.toFixed(1)} and trending ${health.trend.toLowerCase()}.`);

  if (health.dataQualityIssue) {
    parts.push("Health snapshot reports a data quality issue, so the advisory is conservative.");
  }

  if (health.reasonCodes.length > 0) {
    parts.push(`Primary health reason: ${health.reasonCodes[0]}.`);
  }

  if (fault && fault.faultType !== "NONE") {
    parts.push(
      `Fault model flags ${fault.faultType.replace(/_/g, " ").toLowerCase()} with ${(fault.confidence * 100).toFixed(0)}% confidence and anomaly score ${fault.anomalyScore.toFixed(2)}.`
    );
  }

  if (rul) {
    parts.push(
      `Estimated remaining life is experimental: ${rul.cycles.toFixed(0)} cycles with range ${rul.lowerBound.toFixed(0)}-${rul.upperBound.toFixed(0)}, trending ${rul.trend.toLowerCase()}.`
    );
  }

  if (decision.reasons.length > 0) {
    parts.push(`Decision factors: ${decision.reasons.join(", ")}.`);
  }

  parts.push("Advisory only; no autonomous control action is issued.");
  return parts.join(" ");
}

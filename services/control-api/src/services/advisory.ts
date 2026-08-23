import type { FaultPrediction, HealthSnapshot, MissionAdvisory, RulEstimate } from "../types/contracts";

/**
 * Combines the latest HealthSnapshot, FaultPrediction, and RulEstimate for a
 * mission into a single MissionAdvisory. This is the M6-owned decision logic
 * described in the architecture doc: risk + recommended action, advisory only,
 * never autonomous control.
 *
 * Thresholds here are a starting point for the demo — tune against real
 * scenario data during the 8-16h integration window, and document any change
 * as an ADR since MissionAdvisory is a shared contract.
 */
export function buildMissionAdvisory(params: {
  engineId: string;
  missionId: string;
  correlationId: string;
  health: HealthSnapshot;
  fault?: FaultPrediction;
  rul?: RulEstimate;
  producerVersion: string;
}): MissionAdvisory {
  const { engineId, missionId, correlationId, health, fault, rul, producerVersion } = params;

  const { risk, action, inspectionRequired } = deriveRiskAndAction(health, fault);
  const explanation = buildExplanation(health, fault, rul);

  return {
    engineId,
    missionId,
    correlationId,
    advisoryTime: new Date().toISOString(),
    producerVersion,
    risk,
    action,
    explanation,
    inspectionRequired,
    contributingSignals: {
      healthScore: health.healthScore,
      faultType: fault?.faultType,
      faultConfidence: fault?.confidence,
      rulCycles: rul?.cycles,
    },
    sourceVersions: {
      healthSnapshotVersion: health.producerVersion,
      faultPredictionVersion: fault?.producerVersion,
      rulEstimateVersion: rul?.producerVersion,
    },
  };
}

function deriveRiskAndAction(
  health: HealthSnapshot,
  fault?: FaultPrediction
): { risk: MissionAdvisory["risk"]; action: MissionAdvisory["action"]; inspectionRequired: boolean } {
  const highConfidenceFault = fault && fault.faultType !== "NONE" && fault.confidence >= 0.7;
  const anyFault = fault && fault.faultType !== "NONE";

  if (health.healthScore < 40 || highConfidenceFault) {
    return { risk: "CRITICAL", action: "INSPECT", inspectionRequired: true };
  }
  if (health.healthScore < 60 || (anyFault && fault!.confidence >= 0.5)) {
    return { risk: "HIGH", action: "INSPECT", inspectionRequired: true };
  }
  if (health.healthScore < 80 || health.trend === "DEGRADING") {
    return { risk: "MEDIUM", action: "REDUCE_LOAD", inspectionRequired: false };
  }
  return { risk: "LOW", action: "CONTINUE", inspectionRequired: false };
}

function buildExplanation(health: HealthSnapshot, fault?: FaultPrediction, rul?: RulEstimate): string {
  const parts: string[] = [];

  parts.push(`Health score is ${health.healthScore.toFixed(1)} and trending ${health.trend.toLowerCase()}.`);

  if (health.reasonCodes.length > 0) {
    parts.push(health.reasonCodes[0]);
  }

  if (fault && fault.faultType !== "NONE") {
    parts.push(
      `Fault model flags ${fault.faultType.replace(/_/g, " ").toLowerCase()} with ${(fault.confidence * 100).toFixed(0)}% confidence.`
    );
  }

  if (rul) {
    parts.push(
      `Estimated remaining life (experimental): ${rul.cycles.toFixed(0)} cycles (range ${rul.lowerBound.toFixed(0)}-${rul.upperBound.toFixed(0)}).`
    );
  }

  return parts.join(" ");
}

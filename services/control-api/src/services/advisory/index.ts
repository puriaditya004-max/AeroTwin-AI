import type { FaultPrediction, HealthSnapshot, MissionAdvisory, RulEstimate } from "../../types/contracts";
import { buildExplanation } from "./explanation";
import { deriveAdvisoryDecision } from "./policy";

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
  const decision = deriveAdvisoryDecision({ health, fault, rul });

  return {
    engineId,
    missionId,
    correlationId,
    advisoryTime: new Date().toISOString(),
    producerVersion,
    risk: decision.risk,
    action: decision.action,
    explanation: buildExplanation({ health, fault, rul, decision }),
    inspectionRequired: decision.inspectionRequired,
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

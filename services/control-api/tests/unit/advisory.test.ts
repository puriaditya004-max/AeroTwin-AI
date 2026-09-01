import { describe, it, expect } from "vitest";
import { deriveAdvisoryDecision } from "../../src/services/advisory/policy";
import { buildExplanation } from "../../src/services/advisory/explanation";
import { buildMissionAdvisory } from "../../src/services/advisory";
import type { HealthSnapshot, FaultPrediction, RulEstimate } from "../../src/types/contracts";

const nominalHealth: HealthSnapshot = {
  engineId: "ENG-001",
  missionId: "MSN-001",
  correlationId: "corr-1",
  snapshotTime: "2026-08-22T10:00:00.000Z",
  producerVersion: "rules-1.0.0",
  healthScore: 95.0,
  trend: "STABLE",
  violatedRules: [],
  reasonCodes: [],
  ruleVersion: "rules-2026.08",
  dataQualityIssue: false,
};

const nominalFault: FaultPrediction = {
  engineId: "ENG-001",
  missionId: "MSN-001",
  correlationId: "corr-1",
  predictionTime: "2026-08-22T10:00:00.000Z",
  producerVersion: "fault-1.0.0",
  faultType: "NONE",
  confidence: 0.05,
  anomalyScore: 0.1,
  contributors: [],
};

const nominalRul: RulEstimate = {
  engineId: "ENG-001",
  missionId: "MSN-001",
  correlationId: "corr-1",
  estimateTime: "2026-08-22T10:00:00.000Z",
  producerVersion: "rul-1.0.0",
  cycles: 1200,
  lowerBound: 1000,
  upperBound: 1400,
  trend: "STABLE",
  experimental: true,
  basis: "ML_REGRESSION",
};

describe("Advisory Policy", () => {
  it("evaluates nominal conditions as LOW risk and CONTINUE action", () => {
    const decision = deriveAdvisoryDecision({
      health: nominalHealth,
      fault: nominalFault,
      rul: nominalRul,
    });
    expect(decision.risk).toBe("LOW");
    expect(decision.action).toBe("CONTINUE");
    expect(decision.inspectionRequired).toBe(false);
  });

  it("evaluates critical health (< 40) as CRITICAL risk and INSPECT action", () => {
    const criticalHealth: HealthSnapshot = { ...nominalHealth, healthScore: 35.0, trend: "DEGRADING" };
    const decision = deriveAdvisoryDecision({ health: criticalHealth });
    expect(decision.risk).toBe("CRITICAL");
    expect(decision.action).toBe("INSPECT");
    expect(decision.inspectionRequired).toBe(true);
    expect(decision.reasons).toContain("health_critical");
  });

  it("evaluates high-confidence fault (>= 0.70) as CRITICAL risk", () => {
    const fault: FaultPrediction = {
      ...nominalFault,
      faultType: "OIL_PRESSURE_DEGRADATION",
      confidence: 0.85,
      anomalyScore: 0.8,
    };
    const decision = deriveAdvisoryDecision({ health: nominalHealth, fault });
    expect(decision.risk).toBe("CRITICAL");
    expect(decision.action).toBe("INSPECT");
    expect(decision.inspectionRequired).toBe(true);
    expect(decision.reasons).toContain("high_confidence_fault");
  });

  it("evaluates critical RUL lower bound (<= 150) as CRITICAL risk", () => {
    const rul: RulEstimate = { ...nominalRul, cycles: 200, lowerBound: 120, trend: "DEGRADING" };
    const decision = deriveAdvisoryDecision({ health: nominalHealth, rul });
    expect(decision.risk).toBe("CRITICAL");
    expect(decision.action).toBe("INSPECT");
    expect(decision.inspectionRequired).toBe(true);
    expect(decision.reasons).toContain("rul_lower_bound_critical");
  });

  it("evaluates moderate fault confidence / high anomaly as HIGH risk and INSPECT", () => {
    const fault: FaultPrediction = {
      ...nominalFault,
      faultType: "OVERHEATING",
      confidence: 0.55,
      anomalyScore: 0.8,
    };
    const decision = deriveAdvisoryDecision({ health: nominalHealth, fault });
    expect(decision.risk).toBe("HIGH");
    expect(decision.action).toBe("INSPECT");
    expect(decision.inspectionRequired).toBe(true);
  });

  it("evaluates degrading health / sub-threshold score (< 80) as MEDIUM risk and REDUCE_LOAD", () => {
    const health: HealthSnapshot = { ...nominalHealth, healthScore: 75.0, trend: "DEGRADING" };
    const decision = deriveAdvisoryDecision({ health });
    expect(decision.risk).toBe("MEDIUM");
    expect(decision.action).toBe("REDUCE_LOAD");
    expect(decision.inspectionRequired).toBe(false);
  });

  it("evaluates sensor data quality issues conservatively as MEDIUM risk", () => {
    const healthWithDataIssue: HealthSnapshot = {
      ...nominalHealth,
      healthScore: 90.0,
      dataQualityIssue: true,
    };
    const decision = deriveAdvisoryDecision({ health: healthWithDataIssue });
    expect(decision.risk).toBe("MEDIUM");
    expect(decision.action).toBe("REDUCE_LOAD");
    expect(decision.reasons).toContain("health_data_quality_issue");
  });

  it("operates gracefully with health-only input", () => {
    const decision = deriveAdvisoryDecision({ health: nominalHealth });
    expect(decision.risk).toBe("LOW");
    expect(decision.action).toBe("CONTINUE");
  });
});

describe("Advisory Explanation Builder", () => {
  it("omits fault model mention when faultType is NONE", () => {
    const decision = deriveAdvisoryDecision({ health: nominalHealth, fault: nominalFault });
    const text = buildExplanation({ health: nominalHealth, fault: nominalFault, decision });
    expect(text).not.toContain("Fault model flags");
    expect(text).toContain("Health score is 95.0");
    expect(text).toContain("Advisory only; no autonomous control action is issued.");
  });

  it("includes fault details when a fault is detected", () => {
    const fault: FaultPrediction = {
      ...nominalFault,
      faultType: "OIL_PRESSURE_DEGRADATION",
      confidence: 0.87,
      anomalyScore: 0.74,
    };
    const decision = deriveAdvisoryDecision({ health: nominalHealth, fault });
    const text = buildExplanation({ health: nominalHealth, fault, decision });
    expect(text).toContain("oil pressure degradation with 87% confidence");
  });

  it("clearly marks RUL as experimental with uncertainty range", () => {
    const decision = deriveAdvisoryDecision({ health: nominalHealth, rul: nominalRul });
    const text = buildExplanation({ health: nominalHealth, rul: nominalRul, decision });
    expect(text).toContain("Estimated remaining life is experimental: 1200 cycles with range 1000-1400");
  });

  it("notes data quality limitations when dataQualityIssue is true", () => {
    const healthWithQuality: HealthSnapshot = { ...nominalHealth, dataQualityIssue: true };
    const decision = deriveAdvisoryDecision({ health: healthWithQuality });
    const text = buildExplanation({ health: healthWithQuality, decision });
    expect(text).toContain("Health snapshot reports a data quality issue");
  });
});

describe("MissionAdvisory Construction", () => {
  it("builds a complete traceable MissionAdvisory object", () => {
    const advisory = buildMissionAdvisory({
      engineId: "ENG-001",
      missionId: "MSN-001",
      correlationId: "corr-xyz",
      health: nominalHealth,
      fault: nominalFault,
      rul: nominalRul,
      producerVersion: "control-api-1.0.0",
    });

    expect(advisory.engineId).toBe("ENG-001");
    expect(advisory.missionId).toBe("MSN-001");
    expect(advisory.risk).toBe("LOW");
    expect(advisory.action).toBe("CONTINUE");
    expect(advisory.inspectionRequired).toBe(false);
    expect(advisory.contributingSignals?.healthScore).toBe(95.0);
    expect(advisory.sourceVersions?.healthSnapshotVersion).toBe("rules-1.0.0");
    expect(advisory.sourceVersions?.faultPredictionVersion).toBe("fault-1.0.0");
    expect(advisory.sourceVersions?.rulEstimateVersion).toBe("rul-1.0.0");
  });
});

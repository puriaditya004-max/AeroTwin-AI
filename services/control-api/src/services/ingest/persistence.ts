import type { HealthSnapshot, FaultPrediction, RulEstimate } from "../../types/contracts";
import { prisma } from "../../lib/prisma";

export async function ensureMission(engineId: string, missionId: string): Promise<void> {
  await prisma.engine.upsert({
    where: { id: engineId },
    update: {},
    create: { id: engineId },
  });

  await prisma.mission.upsert({
    where: { id: missionId },
    update: { engineId },
    create: { id: missionId, engineId, status: "RUNNING" },
  });
}

export async function persistHealthSnapshot(health: HealthSnapshot): Promise<void> {
  await prisma.healthSnapshot.create({
    data: {
      missionId: health.missionId,
      correlationId: health.correlationId,
      snapshotTime: new Date(health.snapshotTime),
      healthScore: health.healthScore,
      trend: health.trend,
      violatedRules: health.violatedRules,
      reasonCodes: health.reasonCodes,
      ruleVersion: health.ruleVersion,
      producerVersion: health.producerVersion,
      raw: health as unknown as object,
    },
  });
}

export async function persistFaultPrediction(fault: FaultPrediction): Promise<void> {
  await prisma.prediction.create({
    data: {
      missionId: fault.missionId,
      correlationId: fault.correlationId,
      kind: "FAULT",
      predictionTime: new Date(fault.predictionTime),
      faultType: fault.faultType,
      confidence: fault.confidence,
      anomalyScore: fault.anomalyScore,
      producerVersion: fault.producerVersion,
      raw: fault as unknown as object,
    },
  });
}

export async function persistRulEstimate(rul: RulEstimate): Promise<void> {
  await prisma.prediction.create({
    data: {
      missionId: rul.missionId,
      correlationId: rul.correlationId,
      kind: "RUL",
      predictionTime: new Date(rul.estimateTime),
      cycles: rul.cycles,
      lowerBound: rul.lowerBound,
      upperBound: rul.upperBound,
      rulTrend: rul.trend,
      experimental: rul.experimental,
      producerVersion: rul.producerVersion,
      raw: rul as unknown as object,
    },
  });
}

export function hydrateHealthFromRow(row: { raw: unknown }): HealthSnapshot {
  return row.raw as HealthSnapshot;
}

export function hydrateFaultFromRow(row: { raw: unknown } | null): FaultPrediction | undefined {
  return row ? (row.raw as FaultPrediction) : undefined;
}

export function hydrateRulFromRow(row: { raw: unknown } | null): RulEstimate | undefined {
  return row ? (row.raw as RulEstimate) : undefined;
}

import { Prisma } from "@prisma/client";
import type { HealthSnapshot, FaultPrediction, RulEstimate } from "../../types/contracts";
import { prisma } from "../../lib/prisma";
import type { IdempotencyResult } from "./idempotency";

export class UnprocessableEntityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UnprocessableEntityError";
  }
}

export async function ensureMission(
  engineId: string,
  missionId: string,
  client: Prisma.TransactionClient | typeof prisma = prisma
): Promise<void> {
  if (!engineId || typeof engineId !== "string" || !engineId.trim()) {
    throw new UnprocessableEntityError("engineId is required to resolve mission");
  }
  if (!missionId || typeof missionId !== "string" || !missionId.trim()) {
    throw new UnprocessableEntityError("missionId is required to resolve mission");
  }

  await client.engine.upsert({
    where: { id: engineId.trim() },
    update: {},
    create: { id: engineId.trim() },
  });

  await client.mission.upsert({
    where: { id: missionId.trim() },
    update: { engineId: engineId.trim() },
    create: { id: missionId.trim(), engineId: engineId.trim(), status: "RUNNING" },
  });
}

export async function persistHealthSnapshotTx(
  health: HealthSnapshot,
  idempotencyParams: { key: string; payloadHash: string }
): Promise<IdempotencyResult> {
  return prisma.$transaction(async (tx) => {
    await ensureMission(health.engineId, health.missionId, tx);

    const existing = await tx.ingestEvent.findUnique({ where: { key: idempotencyParams.key } });
    if (existing) {
      if (existing.payloadHash === idempotencyParams.payloadHash) {
        return { status: "duplicate", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
      }
      return {
        status: "conflict",
        key: idempotencyParams.key,
        payloadHash: idempotencyParams.payloadHash,
        existingPayloadHash: existing.payloadHash,
      };
    }

    try {
      await tx.ingestEvent.create({
        data: {
          key: idempotencyParams.key,
          kind: "HEALTH",
          missionId: health.missionId,
          correlationId: health.correlationId,
          payloadHash: idempotencyParams.payloadHash,
        },
      });

      await tx.healthSnapshot.create({
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

      return { status: "fresh", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
    } catch (err) {
      if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2002") {
        const raced = await tx.ingestEvent.findUniqueOrThrow({ where: { key: idempotencyParams.key } });
        if (raced.payloadHash === idempotencyParams.payloadHash) {
          return { status: "duplicate", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
        }
        return {
          status: "conflict",
          key: idempotencyParams.key,
          payloadHash: idempotencyParams.payloadHash,
          existingPayloadHash: raced.payloadHash,
        };
      }
      throw err;
    }
  });
}

export async function persistFaultPredictionTx(
  fault: FaultPrediction,
  idempotencyParams: { key: string; payloadHash: string }
): Promise<IdempotencyResult> {
  return prisma.$transaction(async (tx) => {
    await ensureMission(fault.engineId, fault.missionId, tx);

    const existing = await tx.ingestEvent.findUnique({ where: { key: idempotencyParams.key } });
    if (existing) {
      if (existing.payloadHash === idempotencyParams.payloadHash) {
        return { status: "duplicate", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
      }
      return {
        status: "conflict",
        key: idempotencyParams.key,
        payloadHash: idempotencyParams.payloadHash,
        existingPayloadHash: existing.payloadHash,
      };
    }

    try {
      await tx.ingestEvent.create({
        data: {
          key: idempotencyParams.key,
          kind: "FAULT",
          missionId: fault.missionId,
          correlationId: fault.correlationId,
          payloadHash: idempotencyParams.payloadHash,
        },
      });

      await tx.prediction.create({
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

      return { status: "fresh", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
    } catch (err) {
      if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2002") {
        const raced = await tx.ingestEvent.findUniqueOrThrow({ where: { key: idempotencyParams.key } });
        if (raced.payloadHash === idempotencyParams.payloadHash) {
          return { status: "duplicate", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
        }
        return {
          status: "conflict",
          key: idempotencyParams.key,
          payloadHash: idempotencyParams.payloadHash,
          existingPayloadHash: raced.payloadHash,
        };
      }
      throw err;
    }
  });
}

export async function persistRulEstimateTx(
  rul: RulEstimate,
  idempotencyParams: { key: string; payloadHash: string }
): Promise<IdempotencyResult> {
  return prisma.$transaction(async (tx) => {
    await ensureMission(rul.engineId, rul.missionId, tx);

    const existing = await tx.ingestEvent.findUnique({ where: { key: idempotencyParams.key } });
    if (existing) {
      if (existing.payloadHash === idempotencyParams.payloadHash) {
        return { status: "duplicate", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
      }
      return {
        status: "conflict",
        key: idempotencyParams.key,
        payloadHash: idempotencyParams.payloadHash,
        existingPayloadHash: existing.payloadHash,
      };
    }

    try {
      await tx.ingestEvent.create({
        data: {
          key: idempotencyParams.key,
          kind: "RUL",
          missionId: rul.missionId,
          correlationId: rul.correlationId,
          payloadHash: idempotencyParams.payloadHash,
        },
      });

      await tx.prediction.create({
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

      return { status: "fresh", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
    } catch (err) {
      if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2002") {
        const raced = await tx.ingestEvent.findUniqueOrThrow({ where: { key: idempotencyParams.key } });
        if (raced.payloadHash === idempotencyParams.payloadHash) {
          return { status: "duplicate", key: idempotencyParams.key, payloadHash: idempotencyParams.payloadHash };
        }
        return {
          status: "conflict",
          key: idempotencyParams.key,
          payloadHash: idempotencyParams.payloadHash,
          existingPayloadHash: raced.payloadHash,
        };
      }
      throw err;
    }
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


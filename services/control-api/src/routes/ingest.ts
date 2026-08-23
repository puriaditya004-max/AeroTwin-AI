import { Router } from "express";
import { prisma } from "../lib/prisma";
import { validateBody } from "../middleware/validate";
import { HealthSnapshotSchema, FaultPredictionSchema, RulEstimateSchema } from "../types/contracts";
import { emitHealthUpdated, emitFaultPredicted, emitAdvisoryUpdated } from "../sockets";
import { buildMissionAdvisory } from "../services/advisory";
import { logAudit } from "../services/audit";

export const ingestRouter = Router();

const ADVISORY_PRODUCER_VERSION = "control-api-0.1.0";

/**
 * POST /ingest/health  — M3 pushes HealthSnapshot here.
 * Persists it, broadcasts to subscribed HMI clients, and recomputes the
 * mission advisory using the latest known fault/RUL data for this mission.
 */
ingestRouter.post("/health", validateBody(HealthSnapshotSchema), async (req, res) => {
  const health = req.body as import("../types/contracts").HealthSnapshot;

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

  emitHealthUpdated(health.missionId, health);

  await recomputeAndBroadcastAdvisory(health.missionId, health.engineId, health.correlationId, health);

  res.status(202).json({ status: "accepted" });
});

/**
 * POST /ingest/fault — M4 pushes FaultPrediction here.
 */
ingestRouter.post("/fault", validateBody(FaultPredictionSchema), async (req, res) => {
  const fault = req.body as import("../types/contracts").FaultPrediction;

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

  emitFaultPredicted(fault.missionId, fault);

  const latestHealth = await prisma.healthSnapshot.findFirst({
    where: { missionId: fault.missionId },
    orderBy: { snapshotTime: "desc" },
  });

  if (latestHealth) {
    await recomputeAndBroadcastAdvisory(
      fault.missionId,
      /* engineId */ (await prisma.mission.findUniqueOrThrow({ where: { id: fault.missionId } })).engineId,
      fault.correlationId,
      hydrateHealthFromRow(latestHealth),
      fault
    );
  }

  res.status(202).json({ status: "accepted" });
});

/**
 * POST /ingest/rul — M5 pushes RulEstimate here.
 */
ingestRouter.post("/rul", validateBody(RulEstimateSchema), async (req, res) => {
  const rul = req.body as import("../types/contracts").RulEstimate;

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

  // RUL doesn't trigger an immediate advisory recompute on its own in this
  // baseline — it's folded in the next time health or fault triggers one.
  // Adjust if the team decides RUL crossing a threshold should be its own trigger.

  res.status(202).json({ status: "accepted" });
});

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function hydrateHealthFromRow(row: {
  raw: unknown;
}): import("../types/contracts").HealthSnapshot {
  return row.raw as import("../types/contracts").HealthSnapshot;
}

async function recomputeAndBroadcastAdvisory(
  missionId: string,
  engineId: string,
  correlationId: string,
  health: import("../types/contracts").HealthSnapshot,
  faultOverride?: import("../types/contracts").FaultPrediction
): Promise<void> {
  const latestFaultRow =
    faultOverride ??
    (await prisma.prediction
      .findFirst({ where: { missionId, kind: "FAULT" }, orderBy: { predictionTime: "desc" } })
      .then((row) => (row ? (row.raw as unknown as import("../types/contracts").FaultPrediction) : undefined)));

  const latestRulRow = await prisma.prediction
    .findFirst({ where: { missionId, kind: "RUL" }, orderBy: { predictionTime: "desc" } })
    .then((row) => (row ? (row.raw as unknown as import("../types/contracts").RulEstimate) : undefined));

  const advisory = buildMissionAdvisory({
    engineId,
    missionId,
    correlationId,
    health,
    fault: latestFaultRow,
    rul: latestRulRow,
    producerVersion: ADVISORY_PRODUCER_VERSION,
  });

  await prisma.advisory.create({
    data: {
      missionId: advisory.missionId,
      correlationId: advisory.correlationId,
      advisoryTime: new Date(advisory.advisoryTime),
      risk: advisory.risk,
      action: advisory.action,
      explanation: advisory.explanation,
      inspectionRequired: advisory.inspectionRequired,
      producerVersion: advisory.producerVersion,
      raw: advisory as unknown as object,
    },
  });

  emitAdvisoryUpdated(missionId, advisory);

  if (advisory.risk === "CRITICAL" || advisory.risk === "HIGH") {
    await logAudit({
      missionId,
      action: "ADVISORY_HIGH_RISK",
      detail: { risk: advisory.risk, action: advisory.action },
    });
  }
}

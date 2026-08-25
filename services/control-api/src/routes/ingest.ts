import { Router } from "express";
import { prisma } from "../lib/prisma";
import { validateBody } from "../middleware/validate";
import { HealthSnapshotSchema, FaultPredictionSchema, RulEstimateSchema } from "../types/contracts";
import { emitHealthUpdated, emitFaultPredicted, emitRulUpdated, emitAdvisoryUpdated } from "../sockets";
import { buildMissionAdvisory } from "../services/advisory";
import { logAudit } from "../services/audit";
import { buildIdempotencyKey, hashPayload, reserveIdempotencyKey, type PayloadKind } from "../services/ingest/idempotency";
import {
  ensureMission,
  hydrateFaultFromRow,
  hydrateHealthFromRow,
  hydrateRulFromRow,
  persistFaultPrediction,
  persistHealthSnapshot,
  persistRulEstimate,
} from "../services/ingest/persistence";
import { logEvent, nowMs } from "../services/logging";

export const ingestRouter = Router();

const ADVISORY_PRODUCER_VERSION = process.env.M6_ADVISORY_PRODUCER_VERSION ?? "control-api-0.2.0";

/**
 * POST /ingest/health  — M3 pushes HealthSnapshot here.
 * Persists it, broadcasts to subscribed HMI clients, and recomputes the
 * mission advisory using the latest known fault/RUL data for this mission.
 */
ingestRouter.post("/health", validateBody(HealthSnapshotSchema), async (req, res) => {
  const startedAt = nowMs();
  const health = req.body as import("../types/contracts").HealthSnapshot;
  await ensureMission(health.engineId, health.missionId);
  const idempotency = await applyIdempotency(req.header("X-Idempotency-Key"), "HEALTH", health, health.snapshotTime);
  if (idempotency.status === "duplicate") {
    res.status(202).json({ status: "accepted", duplicate: true, idempotencyKey: idempotency.key });
    return;
  }
  if (idempotency.status === "conflict") {
    res.status(409).json({ error: "IDEMPOTENCY_CONFLICT", idempotencyKey: idempotency.key });
    return;
  }

  await persistHealthSnapshot(health);

  emitHealthUpdated(health.missionId, health);

  await recomputeAndBroadcastAdvisory(health.missionId, health.engineId, health.correlationId, health);

  logIngest("HEALTH", health.missionId, health.engineId, health.correlationId, startedAt, "accepted");

  res.status(202).json({ status: "accepted" });
});

/**
 * POST /ingest/fault — M4 pushes FaultPrediction here.
 */
ingestRouter.post("/fault", validateBody(FaultPredictionSchema), async (req, res) => {
  const startedAt = nowMs();
  const fault = req.body as import("../types/contracts").FaultPrediction;
  await ensureMission(fault.engineId, fault.missionId);
  const idempotency = await applyIdempotency(req.header("X-Idempotency-Key"), "FAULT", fault, fault.predictionTime);
  if (idempotency.status === "duplicate") {
    res.status(202).json({ status: "accepted", duplicate: true, idempotencyKey: idempotency.key });
    return;
  }
  if (idempotency.status === "conflict") {
    res.status(409).json({ error: "IDEMPOTENCY_CONFLICT", idempotencyKey: idempotency.key });
    return;
  }

  await persistFaultPrediction(fault);

  emitFaultPredicted(fault.missionId, fault);

  const latestHealth = await prisma.healthSnapshot.findFirst({
    where: { missionId: fault.missionId },
    orderBy: { snapshotTime: "desc" },
  });

  if (latestHealth) {
    await recomputeAndBroadcastAdvisory(
      fault.missionId,
      fault.engineId,
      fault.correlationId,
      hydrateHealthFromRow(latestHealth),
      fault
    );
  }

  logIngest("FAULT", fault.missionId, fault.engineId, fault.correlationId, startedAt, latestHealth ? "accepted" : "waiting_for_health");

  res.status(202).json({ status: "accepted", advisory: latestHealth ? "updated" : "waiting_for_health" });
});

/**
 * POST /ingest/rul — M5 pushes RulEstimate here.
 */
ingestRouter.post("/rul", validateBody(RulEstimateSchema), async (req, res) => {
  const startedAt = nowMs();
  const rul = req.body as import("../types/contracts").RulEstimate;
  await ensureMission(rul.engineId, rul.missionId);
  const idempotency = await applyIdempotency(req.header("X-Idempotency-Key"), "RUL", rul, rul.estimateTime);
  if (idempotency.status === "duplicate") {
    res.status(202).json({ status: "accepted", duplicate: true, idempotencyKey: idempotency.key });
    return;
  }
  if (idempotency.status === "conflict") {
    res.status(409).json({ error: "IDEMPOTENCY_CONFLICT", idempotencyKey: idempotency.key });
    return;
  }

  await persistRulEstimate(rul);

  emitRulUpdated(rul.missionId, rul);

  const latestHealth = await prisma.healthSnapshot.findFirst({
    where: { missionId: rul.missionId },
    orderBy: { snapshotTime: "desc" },
  });

  if (latestHealth) {
    await recomputeAndBroadcastAdvisory(
      rul.missionId,
      rul.engineId,
      rul.correlationId,
      hydrateHealthFromRow(latestHealth),
      undefined,
      rul
    );
  }

  logIngest("RUL", rul.missionId, rul.engineId, rul.correlationId, startedAt, latestHealth ? "accepted" : "waiting_for_health");

  res.status(202).json({ status: "accepted", advisory: latestHealth ? "updated" : "waiting_for_health" });
});

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function recomputeAndBroadcastAdvisory(
  missionId: string,
  engineId: string,
  correlationId: string,
  health: import("../types/contracts").HealthSnapshot,
  faultOverride?: import("../types/contracts").FaultPrediction,
  rulOverride?: import("../types/contracts").RulEstimate
): Promise<void> {
  const latestFaultRow =
    faultOverride ??
    (await prisma.prediction
      .findFirst({ where: { missionId, kind: "FAULT" }, orderBy: { predictionTime: "desc" } })
      .then(hydrateFaultFromRow));

  const latestRulRow =
    rulOverride ??
    (await prisma.prediction
      .findFirst({ where: { missionId, kind: "RUL" }, orderBy: { predictionTime: "desc" } })
      .then(hydrateRulFromRow));

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
  logEvent("info", "advisory.created", {
    missionId,
    engineId,
    correlationId,
    advisoryRisk: advisory.risk,
    action: advisory.action,
  });

  if (advisory.risk === "CRITICAL" || advisory.risk === "HIGH") {
    await logAudit({
      missionId,
      action: "ADVISORY_HIGH_RISK",
      detail: { risk: advisory.risk, action: advisory.action },
    });
  }
}

async function applyIdempotency(
  headerValue: string | undefined,
  kind: PayloadKind,
  payload: { missionId: string; correlationId: string },
  eventTime: string
) {
  const key = buildIdempotencyKey({
    headerValue,
    kind,
    missionId: payload.missionId,
    correlationId: payload.correlationId,
    eventTime,
  });
  return reserveIdempotencyKey({
    key,
    payloadHash: hashPayload(payload),
    missionId: payload.missionId,
    correlationId: payload.correlationId,
    kind,
  });
}

function logIngest(
  payloadKind: PayloadKind,
  missionId: string,
  engineId: string,
  correlationId: string,
  startedAt: number,
  status: string
): void {
  logEvent("info", "ingest.accepted", {
    route: `/ingest/${payloadKind.toLowerCase()}`,
    missionId,
    engineId,
    correlationId,
    payloadKind,
    latencyMs: nowMs() - startedAt,
    status,
  });
}

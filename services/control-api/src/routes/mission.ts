import { Router } from "express";
import { z } from "zod";
import { prisma } from "../lib/prisma";
import { validateBody } from "../middleware/validate";
import { requireAuth, requireRole } from "../middleware/auth";
import { logAudit } from "../services/audit";

export const missionRouter = Router();

const StartMissionSchema = z.object({
  missionId: z.string(),
  engineId: z.string(),
  scenarioId: z.string().optional(),
});

/**
 * POST /missions — start a new mission run. Operator/Admin only.
 */
missionRouter.post(
  "/",
  requireAuth,
  requireRole("ADMIN", "OPERATOR"),
  validateBody(StartMissionSchema),
  async (req, res) => {
    const { missionId, engineId, scenarioId } = req.body as z.infer<typeof StartMissionSchema>;

    await prisma.engine.upsert({
      where: { id: engineId },
      update: {},
      create: { id: engineId },
    });

    const mission = await prisma.mission.create({
      data: { id: missionId, engineId, scenarioId, status: "RUNNING" },
    });

    await logAudit({
      missionId,
      userId: req.user?.id,
      action: "MISSION_STARTED",
      detail: { engineId, scenarioId },
    });

    res.status(201).json(mission);
  }
);

/**
 * GET /missions/:missionId/advisories — replay/audit trail of advisories for a mission.
 */
missionRouter.get("/:missionId/advisories", requireAuth, async (req, res) => {
  const advisories = await prisma.advisory.findMany({
    where: { missionId: req.params.missionId },
    orderBy: { advisoryTime: "asc" },
  });
  res.json(advisories);
});

/**
 * GET /missions/:missionId/advisories/latest — current advisory for the HMI dashboard.
 */
missionRouter.get("/:missionId/advisories/latest", requireAuth, async (req, res) => {
  const advisory = await prisma.advisory.findFirst({
    where: { missionId: req.params.missionId },
    orderBy: { advisoryTime: "desc" },
  });
  if (!advisory) {
    res.status(404).json({ error: "NO_ADVISORY_YET" });
    return;
  }
  res.json(advisory);
});

/**
 * GET /missions/:missionId/state — combined latest snapshot for HMI initial load.
 * Fixes the "page refresh shows nothing" gap: the HMI's Socket.IO connection
 * only delivers events that arrive AFTER it subscribes, so on mount (or a
 * refresh mid-mission) it must fetch the current state via REST first, then
 * let live socket events take over from there.
 */
missionRouter.get("/:missionId/state", requireAuth, async (req, res) => {
  const { missionId } = req.params;

  const [health, faultRow, rulRow, advisory] = await Promise.all([
    prisma.healthSnapshot.findFirst({ where: { missionId }, orderBy: { snapshotTime: "desc" } }),
    prisma.prediction.findFirst({ where: { missionId, kind: "FAULT" }, orderBy: { predictionTime: "desc" } }),
    prisma.prediction.findFirst({ where: { missionId, kind: "RUL" }, orderBy: { predictionTime: "desc" } }),
    prisma.advisory.findFirst({ where: { missionId }, orderBy: { advisoryTime: "desc" } }),
  ]);

  res.json({
    health: health?.raw ?? null,
    fault: faultRow?.raw ?? null,
    rul: rulRow?.raw ?? null,
    advisory: advisory?.raw ?? null,
  });
});

/**
 * POST /missions/:missionId/end — mark mission complete.
 */
missionRouter.post("/:missionId/end", requireAuth, requireRole("ADMIN", "OPERATOR"), async (req, res) => {
  const mission = await prisma.mission.update({
    where: { id: req.params.missionId },
    data: { status: "COMPLETED", endedAt: new Date() },
  });

  await logAudit({ missionId: mission.id, userId: req.user?.id, action: "MISSION_ENDED" });

  res.json(mission);
});
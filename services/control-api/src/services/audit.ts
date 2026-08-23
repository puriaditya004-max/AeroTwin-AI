import { Prisma } from "@prisma/client";
import { prisma } from "../lib/prisma";

/**
 * Writes an audit entry. Never throws into the request path — logging failures
 * should not break the operator's actual request. Errors are swallowed after
 * being logged to stderr; wire this to Sentry later if it needs alerting.
 */
export async function logAudit(params: {
  missionId?: string;
  userId?: string;
  action: string;
  detail?: Record<string, unknown>;
}): Promise<void> {
  try {
    await prisma.auditEntry.create({
      data: {
        missionId: params.missionId,
        userId: params.userId,
        action: params.action,
        detail: params.detail as Prisma.InputJsonValue | undefined,
      },
    });
  } catch (err) {
    console.error("[audit] failed to write audit entry:", err);
  }
}
import { createHash } from "crypto";
import { Prisma } from "@prisma/client";
import { prisma } from "../../lib/prisma";

export type PayloadKind = "HEALTH" | "FAULT" | "RUL";

export type IdempotencyResult =
  | { status: "fresh"; key: string; payloadHash: string }
  | { status: "duplicate"; key: string; payloadHash: string }
  | { status: "conflict"; key: string; payloadHash: string; existingPayloadHash: string };

export function buildIdempotencyKey(params: {
  headerValue?: string;
  kind: PayloadKind;
  missionId: string;
  correlationId: string;
  eventTime: string;
}): string {
  return params.headerValue?.trim() || `${params.kind}:${params.missionId}:${params.correlationId}:${params.eventTime}`;
}

export function hashPayload(payload: unknown): string {
  return createHash("sha256").update(stableStringify(payload)).digest("hex");
}

export async function reserveIdempotencyKey(params: {
  key: string;
  payloadHash: string;
  missionId: string;
  correlationId: string;
  kind: PayloadKind;
}): Promise<IdempotencyResult> {
  const existing = await prisma.ingestEvent.findUnique({ where: { key: params.key } });
  if (existing) {
    if (existing.payloadHash === params.payloadHash) {
      return { status: "duplicate", key: params.key, payloadHash: params.payloadHash };
    }
    return {
      status: "conflict",
      key: params.key,
      payloadHash: params.payloadHash,
      existingPayloadHash: existing.payloadHash,
    };
  }

  try {
    await prisma.ingestEvent.create({
      data: {
        key: params.key,
        kind: params.kind,
        missionId: params.missionId,
        correlationId: params.correlationId,
        payloadHash: params.payloadHash,
      },
    });
    return { status: "fresh", key: params.key, payloadHash: params.payloadHash };
  } catch (err) {
    if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2002") {
      const raced = await prisma.ingestEvent.findUniqueOrThrow({ where: { key: params.key } });
      if (raced.payloadHash === params.payloadHash) {
        return { status: "duplicate", key: params.key, payloadHash: params.payloadHash };
      }
      return {
        status: "conflict",
        key: params.key,
        payloadHash: params.payloadHash,
        existingPayloadHash: raced.payloadHash,
      };
    }
    throw err;
  }
}

function stableStringify(value: unknown): string {
  return JSON.stringify(sortObject(value));
}

function sortObject(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortObject);
  if (value && typeof value === "object") {
    return Object.keys(value as Record<string, unknown>)
      .sort()
      .reduce<Record<string, unknown>>((acc, key) => {
        acc[key] = sortObject((value as Record<string, unknown>)[key]);
        return acc;
      }, {});
  }
  return value;
}

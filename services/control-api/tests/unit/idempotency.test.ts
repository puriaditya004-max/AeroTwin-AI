import { describe, it, expect } from "vitest";
import { buildIdempotencyKey, hashPayload } from "../../src/services/ingest/idempotency";

describe("Idempotency Helpers", () => {
  it("builds a key from header value when provided", () => {
    const key = buildIdempotencyKey({
      headerValue: "custom-header-key-123",
      kind: "HEALTH",
      missionId: "MSN-001",
      correlationId: "corr-1",
      eventTime: "2026-08-22T10:00:00.000Z",
    });
    expect(key).toBe("custom-header-key-123");
  });

  it("builds a fallback key from payload coordinates when header is missing", () => {
    const key = buildIdempotencyKey({
      kind: "FAULT",
      missionId: "MSN-001",
      correlationId: "corr-1",
      eventTime: "2026-08-22T10:00:00.000Z",
    });
    expect(key).toBe("FAULT:MSN-001:corr-1:2026-08-22T10:00:00.000Z");
  });

  it("produces deterministic hash regardless of key order in object", () => {
    const objA = { b: 2, a: 1, nested: { y: "hello", x: 10 } };
    const objB = { a: 1, b: 2, nested: { x: 10, y: "hello" } };

    const hashA = hashPayload(objA);
    const hashB = hashPayload(objB);

    expect(hashA).toBe(hashB);
  });

  it("produces different hash when values differ", () => {
    const objA = { score: 95.0 };
    const objB = { score: 95.1 };

    expect(hashPayload(objA)).not.toBe(hashPayload(objB));
  });
});

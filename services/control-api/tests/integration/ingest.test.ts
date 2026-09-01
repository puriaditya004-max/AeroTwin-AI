import { describe, it, expect, beforeEach, vi } from "vitest";
import request from "supertest";
import { createApp } from "../../src/server";
import { prisma } from "../../src/lib/prisma";
import type { HealthSnapshot, FaultPrediction, RulEstimate } from "../../src/types/contracts";

const app = createApp();

const sampleHealth: HealthSnapshot = {
  engineId: "ENG-001",
  missionId: "MSN-OILPRESS-001",
  correlationId: "corr-101",
  snapshotTime: "2026-08-22T09:14:32.700Z",
  producerVersion: "1.0.0",
  healthScore: 71.5,
  trend: "DEGRADING",
  subScores: { temperature: 82, pressure: 58, vibration: 95, load: 88 },
  violatedRules: ["RULE_OIL_PRESSURE_LOW"],
  reasonCodes: ["Oil pressure trending below safe envelope"],
  ruleVersion: "rules-2026.08.1",
  dataQualityIssue: false,
};

const sampleFault: FaultPrediction = {
  engineId: "ENG-001",
  missionId: "MSN-OILPRESS-001",
  correlationId: "corr-101",
  predictionTime: "2026-08-22T09:14:32.900Z",
  producerVersion: "fault-clf-1.0.0",
  faultType: "OIL_PRESSURE_DEGRADATION",
  confidence: 0.87,
  anomalyScore: 0.74,
  contributors: [
    { feature: "oilPressureKpa_rollingMean", contribution: 0.42 },
    { feature: "oilPressureKpa_rateOfChange", contribution: 0.31 },
  ],
};

const sampleRul: RulEstimate = {
  engineId: "ENG-001",
  missionId: "MSN-OILPRESS-001",
  correlationId: "corr-101",
  estimateTime: "2026-08-22T09:14:33.000Z",
  producerVersion: "rul-reg-0.1.0",
  cycles: 340,
  lowerBound: 260,
  upperBound: 410,
  trend: "DEGRADING",
  experimental: true,
  basis: "ML_REGRESSION",
};

describe("Ingest Endpoints", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("POST /ingest/health", () => {
    it("accepts valid health snapshot, persists atomically, and returns 202", async () => {
      vi.spyOn(prisma, "$transaction").mockImplementation(async (cb: any) => {
        const mockTx = {
          engine: { upsert: vi.fn().mockResolvedValue({}) },
          mission: { upsert: vi.fn().mockResolvedValue({}) },
          ingestEvent: { findUnique: vi.fn().mockResolvedValue(null), create: vi.fn().mockResolvedValue({}) },
          healthSnapshot: { create: vi.fn().mockResolvedValue({}) },
        };
        return cb(mockTx);
      });

      vi.spyOn(prisma.prediction, "findFirst").mockResolvedValue(null);
      vi.spyOn(prisma.advisory, "create").mockResolvedValue({} as any);

      const res = await request(app).post("/ingest/health").send(sampleHealth);
      expect(res.status).toBe(202);
      expect(res.body.status).toBe("accepted");
    });

    it("rejects invalid payload with 400 and structured issues", async () => {
      const invalidPayload = { ...sampleHealth, healthScore: 150 }; // exceeds max 100
      const res = await request(app).post("/ingest/health").send(invalidPayload);
      expect(res.status).toBe(400);
      expect(res.body.error).toBe("VALIDATION_FAILED");
      expect(res.body.issues).toBeDefined();
    });

    it("handles duplicate event idempotency safely by returning 202 with duplicate: true", async () => {
      vi.spyOn(prisma, "$transaction").mockImplementation(async (cb: any) => {
        const mockTx = {
          engine: { upsert: vi.fn().mockResolvedValue({}) },
          mission: { upsert: vi.fn().mockResolvedValue({}) },
          ingestEvent: {
            findUnique: vi.fn().mockResolvedValue({
              key: "custom-key-1",
              payloadHash: hashPayload(sampleHealth),
            }),
          },
        };
        return cb(mockTx);
      });

      const res = await request(app)
        .post("/ingest/health")
        .set("X-Idempotency-Key", "custom-key-1")
        .send(sampleHealth);

      // Duplicate should accept without re-creating
      expect(res.status).toBe(202);
      expect(res.body.status).toBe("accepted");
      expect(res.body.duplicate).toBe(true);
    });

    it("rejects conflicting payload with same idempotency key with 409 conflict", async () => {
      vi.spyOn(prisma, "$transaction").mockImplementation(async (cb: any) => {
        const mockTx = {
          engine: { upsert: vi.fn().mockResolvedValue({}) },
          mission: { upsert: vi.fn().mockResolvedValue({}) },
          ingestEvent: {
            findUnique: vi.fn().mockResolvedValue({
              key: "custom-key-1",
              payloadHash: "different-hash-from-earlier",
            }),
          },
        };
        return cb(mockTx);
      });

      const res = await request(app)
        .post("/ingest/health")
        .set("X-Idempotency-Key", "custom-key-1")
        .send(sampleHealth);

      expect(res.status).toBe(409);
      expect(res.body.error).toBe("IDEMPOTENCY_CONFLICT");
    });
  });

  describe("POST /ingest/fault", () => {
    it("accepts fault prediction and recomputes advisory when health exists", async () => {
      vi.spyOn(prisma, "$transaction").mockImplementation(async (cb: any) => {
        const mockTx = {
          engine: { upsert: vi.fn().mockResolvedValue({}) },
          mission: { upsert: vi.fn().mockResolvedValue({}) },
          ingestEvent: { findUnique: vi.fn().mockResolvedValue(null), create: vi.fn().mockResolvedValue({}) },
          prediction: { create: vi.fn().mockResolvedValue({}) },
        };
        return cb(mockTx);
      });

      vi.spyOn(prisma.healthSnapshot, "findFirst").mockResolvedValue({ raw: sampleHealth } as any);
      vi.spyOn(prisma.prediction, "findFirst").mockResolvedValue(null);
      vi.spyOn(prisma.advisory, "create").mockResolvedValue({} as any);

      const res = await request(app).post("/ingest/fault").send(sampleFault);
      expect(res.status).toBe(202);
      expect(res.body.status).toBe("accepted");
      expect(res.body.advisory).toBe("updated");
    });

    it("accepts fault prediction and waits for health if no health snapshot exists yet", async () => {
      vi.spyOn(prisma, "$transaction").mockImplementation(async (cb: any) => {
        const mockTx = {
          engine: { upsert: vi.fn().mockResolvedValue({}) },
          mission: { upsert: vi.fn().mockResolvedValue({}) },
          ingestEvent: { findUnique: vi.fn().mockResolvedValue(null), create: vi.fn().mockResolvedValue({}) },
          prediction: { create: vi.fn().mockResolvedValue({}) },
        };
        return cb(mockTx);
      });

      vi.spyOn(prisma.healthSnapshot, "findFirst").mockResolvedValue(null);

      const res = await request(app).post("/ingest/fault").send(sampleFault);
      expect(res.status).toBe(202);
      expect(res.body.status).toBe("accepted");
      expect(res.body.advisory).toBe("waiting_for_health");
    });
  });

  describe("POST /ingest/rul", () => {
    it("accepts RUL estimate and triggers advisory recomputation when health exists", async () => {
      vi.spyOn(prisma, "$transaction").mockImplementation(async (cb: any) => {
        const mockTx = {
          engine: { upsert: vi.fn().mockResolvedValue({}) },
          mission: { upsert: vi.fn().mockResolvedValue({}) },
          ingestEvent: { findUnique: vi.fn().mockResolvedValue(null), create: vi.fn().mockResolvedValue({}) },
          prediction: { create: vi.fn().mockResolvedValue({}) },
        };
        return cb(mockTx);
      });

      vi.spyOn(prisma.healthSnapshot, "findFirst").mockResolvedValue({ raw: sampleHealth } as any);
      vi.spyOn(prisma.prediction, "findFirst").mockResolvedValue(null);
      vi.spyOn(prisma.advisory, "create").mockResolvedValue({} as any);

      const res = await request(app).post("/ingest/rul").send(sampleRul);
      expect(res.status).toBe(202);
      expect(res.body.status).toBe("accepted");
      expect(res.body.advisory).toBe("updated");
    });

    it("accepts RUL estimate safely when no health snapshot exists yet", async () => {
      vi.spyOn(prisma, "$transaction").mockImplementation(async (cb: any) => {
        const mockTx = {
          engine: { upsert: vi.fn().mockResolvedValue({}) },
          mission: { upsert: vi.fn().mockResolvedValue({}) },
          ingestEvent: { findUnique: vi.fn().mockResolvedValue(null), create: vi.fn().mockResolvedValue({}) },
          prediction: { create: vi.fn().mockResolvedValue({}) },
        };
        return cb(mockTx);
      });

      vi.spyOn(prisma.healthSnapshot, "findFirst").mockResolvedValue(null);

      const res = await request(app).post("/ingest/rul").send(sampleRul);
      expect(res.status).toBe(202);
      expect(res.body.status).toBe("accepted");
      expect(res.body.advisory).toBe("waiting_for_health");
    });
  });
});

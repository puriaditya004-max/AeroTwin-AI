import { describe, it, expect, beforeEach, vi } from "vitest";
import request from "supertest";
import jwt from "jsonwebtoken";
import { createApp } from "../../src/server";
import { prisma } from "../../src/lib/prisma";

const JWT_SECRET = process.env.JWT_SECRET || "test-jwt-secret";
process.env.JWT_SECRET = JWT_SECRET;

const app = createApp();

function generateTestToken(role: "ADMIN" | "OPERATOR" | "VIEWER" = "OPERATOR") {
  return jwt.sign({ id: "usr-1", email: `test-${role.toLowerCase()}@aerotwin.local`, role }, JWT_SECRET, {
    expiresIn: "1h",
  });
}

describe("Mission Lifecycle & Query Routes", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("POST /missions starts a mission and writes audit record", async () => {
    const token = generateTestToken("OPERATOR");
    vi.spyOn(prisma.engine, "upsert").mockResolvedValue({ id: "ENG-001", label: null, createdAt: new Date() });
    vi.spyOn(prisma.mission, "create").mockResolvedValue({
      id: "MSN-NEW-001",
      engineId: "ENG-001",
      scenarioId: "oil_pressure_degradation",
      status: "RUNNING",
      startedAt: new Date(),
      endedAt: null,
    });
    vi.spyOn(prisma.auditEntry, "create").mockResolvedValue({} as any);

    const res = await request(app)
      .post("/missions")
      .set("Authorization", `Bearer ${token}`)
      .send({ missionId: "MSN-NEW-001", engineId: "ENG-001", scenarioId: "oil_pressure_degradation" });

    expect(res.status).toBe(201);
    expect(res.body.id).toBe("MSN-NEW-001");
    expect(res.body.status).toBe("RUNNING");
  });

  it("GET /missions lists missions", async () => {
    const token = generateTestToken("VIEWER");
    vi.spyOn(prisma.mission, "findMany").mockResolvedValue([
      {
        id: "MSN-001",
        engineId: "ENG-001",
        scenarioId: "normal_operation",
        status: "COMPLETED",
        startedAt: new Date(),
        endedAt: new Date(),
        engine: { id: "ENG-001", label: "Engine 1", createdAt: new Date() },
      } as any,
    ]);

    const res = await request(app).get("/missions").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].id).toBe("MSN-001");
  });

  it("GET /missions/:id returns mission detail", async () => {
    const token = generateTestToken("VIEWER");
    vi.spyOn(prisma.mission, "findUnique").mockResolvedValue({
      id: "MSN-001",
      engineId: "ENG-001",
      scenarioId: null,
      status: "RUNNING",
      startedAt: new Date(),
      endedAt: null,
      engine: { id: "ENG-001", label: null, createdAt: new Date() },
    } as any);

    const res = await request(app).get("/missions/MSN-001").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe("MSN-001");
  });

  it("GET /missions/:id returns 404 for non-existent mission", async () => {
    const token = generateTestToken("VIEWER");
    vi.spyOn(prisma.mission, "findUnique").mockResolvedValue(null);

    const res = await request(app).get("/missions/MSN-NONEXISTENT").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(404);
    expect(res.body.error).toBe("MISSION_NOT_FOUND");
  });

  it("GET /missions/:id/state aggregates current health, fault, rul, and advisory", async () => {
    const token = generateTestToken("OPERATOR");
    vi.spyOn(prisma.healthSnapshot, "findFirst").mockResolvedValue({ raw: { healthScore: 92.5 } } as any);
    vi.spyOn(prisma.prediction, "findFirst")
      .mockResolvedValueOnce({ raw: { faultType: "NONE" } } as any) // FAULT
      .mockResolvedValueOnce({ raw: { cycles: 850 } } as any); // RUL
    vi.spyOn(prisma.advisory, "findFirst").mockResolvedValue({ raw: { risk: "LOW", action: "CONTINUE" } } as any);

    const res = await request(app).get("/missions/MSN-001/state").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.health.healthScore).toBe(92.5);
    expect(res.body.fault.faultType).toBe("NONE");
    expect(res.body.rul.cycles).toBe(850);
    expect(res.body.advisory.action).toBe("CONTINUE");
  });

  it("GET /missions/:id/advisories returns advisory history", async () => {
    const token = generateTestToken("OPERATOR");
    vi.spyOn(prisma.advisory, "findMany").mockResolvedValue([
      { id: "adv-1", missionId: "MSN-001", risk: "LOW", action: "CONTINUE" } as any,
      { id: "adv-2", missionId: "MSN-001", risk: "HIGH", action: "INSPECT" } as any,
    ]);

    const res = await request(app).get("/missions/MSN-001/advisories").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it("GET /missions/:id/audit returns audit log trail", async () => {
    const token = generateTestToken("OPERATOR");
    vi.spyOn(prisma.auditEntry, "findMany").mockResolvedValue([
      { id: "aud-1", missionId: "MSN-001", action: "MISSION_STARTED", createdAt: new Date() } as any,
    ]);

    const res = await request(app).get("/missions/MSN-001/audit").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].action).toBe("MISSION_STARTED");
  });

  it("POST /missions/:id/end and POST /missions/:id/abort update mission status", async () => {
    const token = generateTestToken("OPERATOR");
    vi.spyOn(prisma.mission, "update")
      .mockResolvedValueOnce({ id: "MSN-001", status: "COMPLETED" } as any)
      .mockResolvedValueOnce({ id: "MSN-001", status: "ABORTED" } as any);
    vi.spyOn(prisma.auditEntry, "create").mockResolvedValue({} as any);

    const resEnd = await request(app).post("/missions/MSN-001/end").set("Authorization", `Bearer ${token}`);
    expect(resEnd.status).toBe(200);
    expect(resEnd.body.status).toBe("COMPLETED");

    const resAbort = await request(app).post("/missions/MSN-001/abort").set("Authorization", `Bearer ${token}`);
    expect(resAbort.status).toBe(200);
    expect(resAbort.body.status).toBe("ABORTED");
  });
});

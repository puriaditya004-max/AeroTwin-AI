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

describe("Authentication & RBAC Routes", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("POST /auth/dev-login issues a valid JWT in development mode", async () => {
    process.env.NODE_ENV = "development";
    vi.spyOn(prisma.user, "upsert").mockResolvedValue({
      id: "usr-dev-operator",
      email: "dev-operator@aerotwin.local",
      passwordHash: "dummy",
      role: "OPERATOR",
      createdAt: new Date(),
    });

    const res = await request(app).post("/auth/dev-login").send({ role: "OPERATOR" });
    expect(res.status).toBe(200);
    expect(res.body.token).toBeDefined();
    expect(res.body.user.role).toBe("OPERATOR");

    const decoded = jwt.verify(res.body.token, JWT_SECRET) as { role: string };
    expect(decoded.role).toBe("OPERATOR");
  });

  it("POST /auth/dev-login returns 404 when NODE_ENV=production", async () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "production";

    const res = await request(app).post("/auth/dev-login").send({ role: "OPERATOR" });
    expect(res.status).toBe(404);
    expect(res.body.error).toBe("NOT_FOUND");

    process.env.NODE_ENV = originalEnv;
  });

  it("rejects unauthenticated requests to protected endpoints with 401", async () => {
    const res = await request(app).get("/missions");
    expect(res.status).toBe(401);
    expect(res.body.error).toBe("UNAUTHENTICATED");
  });

  it("rejects requests with invalid tokens with 401", async () => {
    const res = await request(app).get("/missions").set("Authorization", "Bearer invalid-token-xyz");
    expect(res.status).toBe(401);
    expect(res.body.error).toBe("UNAUTHENTICATED");
  });

  it("allows access to authenticated requests with valid token", async () => {
    const token = generateTestToken("OPERATOR");
    vi.spyOn(prisma.mission, "findMany").mockResolvedValue([]);

    const res = await request(app).get("/missions").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("enforces role requirements (e.g. VIEWER cannot start a mission)", async () => {
    const viewerToken = generateTestToken("VIEWER");

    const res = await request(app)
      .post("/missions")
      .set("Authorization", `Bearer ${viewerToken}`)
      .send({ missionId: "MSN-TEST", engineId: "ENG-TEST" });

    expect(res.status).toBe(403);
    expect(res.body.error).toBe("FORBIDDEN");
  });
});

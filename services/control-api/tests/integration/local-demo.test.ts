import { afterEach, describe, expect, it, vi } from "vitest";
import request from "supertest";
import jwt from "jsonwebtoken";
import { createApp } from "../../src/server";
import { prisma } from "../../src/lib/prisma";

const app = createApp();
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.unstubAllGlobals(); });
describe("Explicit local demo boundary", () => {
  it.each([["deployment", "true"], ["local-demo", "false"]])("denies demo login with %s/%s", async (mode, enabled) => {
    vi.stubEnv("APP_MODE", mode); vi.stubEnv("ENABLE_DEMO_AUTH", enabled);
    expect((await request(app).post("/auth/demo-login")).status).toBe(404);
  });
  it("issues only a viewer token when both demo flags are explicit", async () => {
    vi.stubEnv("APP_MODE", "local-demo"); vi.stubEnv("ENABLE_DEMO_AUTH", "true");
    vi.stubEnv("JWT_SECRET", "test-demo-secret");
    vi.spyOn(prisma.user, "upsert").mockResolvedValue({ id: "demo-viewer" } as any);
    const response = await request(app).post("/auth/demo-login").send({ role: "ADMIN" });
    expect(response.status).toBe(200);
    const token = jwt.verify(response.body.token, "test-demo-secret") as jwt.JwtPayload;
    expect(token.role).toBe("VIEWER");
  });
  it("requires auth and proxies the actual M2 checkpoint", async () => {
    expect((await request(app).get("/missions/MIS-1/telemetry")).status).toBe(401);
    vi.stubEnv("JWT_SECRET", "test-demo-secret");
    const token = jwt.sign({ id: "viewer", role: "VIEWER" }, "test-demo-secret");
    const state = { missionId: "MIS-1", stateQuality: "GOOD", sensors: { rpm: 2450 } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => state }));
    const response = await request(app).get("/missions/MIS-1/telemetry").set("Authorization", `Bearer ${token}`);
    expect(response.status).toBe(200); expect(response.body).toEqual(state);
  });
  it("returns unavailable instead of mock telemetry on M2 failure", async () => {
    vi.stubEnv("JWT_SECRET", "test-demo-secret");
    const token = jwt.sign({ id: "viewer", role: "VIEWER" }, "test-demo-secret");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const response = await request(app).get("/missions/MIS-1/telemetry").set("Authorization", `Bearer ${token}`);
    expect(response.status).toBe(503);
    expect(response.body).toEqual({ error: "TELEMETRY_UNAVAILABLE" });
  });
});

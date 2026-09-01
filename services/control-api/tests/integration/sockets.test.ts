import { describe, it, expect, beforeAll, afterAll } from "vitest";
import http from "http";
import express from "express";
import { io as Client, type Socket as ClientSocket } from "socket.io-client";
import jwt from "jsonwebtoken";
import {
  initSocketServer,
  emitHealthUpdated,
  emitFaultPredicted,
  emitRulUpdated,
  emitAdvisoryUpdated,
} from "../../src/sockets";
import type {
  HealthSnapshot,
  FaultPrediction,
  RulEstimate,
  MissionAdvisory,
} from "../../src/types/contracts";

const JWT_SECRET = process.env.JWT_SECRET || "test-jwt-secret";
process.env.JWT_SECRET = JWT_SECRET;

let httpServer: http.Server;
let port: number;

function generateToken() {
  return jwt.sign({ id: "usr-1", email: "test@aerotwin.local", role: "OPERATOR" }, JWT_SECRET);
}

beforeAll(async () => {
  const app = express();
  httpServer = http.createServer(app);
  initSocketServer(httpServer);

  await new Promise<void>((resolve) => {
    httpServer.listen(0, () => {
      const addr = httpServer.address();
      if (addr && typeof addr === "object") {
        port = addr.port;
      }
      resolve();
    });
  });
});

afterAll(async () => {
  await new Promise<void>((resolve) => {
    httpServer.close(() => resolve());
  });
});

describe("Socket.IO Realtime Hub", () => {
  it("authenticates and connects with valid JWT", async () => {
    const client = Client(`http://localhost:${port}`, {
      auth: { token: generateToken() },
      transports: ["websocket"],
    });

    await new Promise<void>((resolve) => {
      client.on("connect", () => {
        expect(client.connected).toBe(true);
        client.disconnect();
        resolve();
      });
    });
  });

  it("subscribes to mission room and receives mission:subscribed", async () => {
    const client = Client(`http://localhost:${port}`, {
      auth: { token: generateToken() },
      transports: ["websocket"],
    });

    await new Promise<void>((resolve) => {
      client.on("connect", () => {
        client.emit("mission:subscribe", "MSN-REALTIME-001");
      });

      client.on("mission:subscribed", (data) => {
        expect(data.missionId).toBe("MSN-REALTIME-001");
        client.disconnect();
        resolve();
      });
    });
  });

  it("rejects invalid mission ID with mission:error", async () => {
    const client = Client(`http://localhost:${port}`, {
      auth: { token: generateToken() },
      transports: ["websocket"],
    });

    await new Promise<void>((resolve) => {
      client.on("connect", () => {
        client.emit("mission:subscribe", "   "); // blank
      });

      client.on("mission:error", (err) => {
        expect(err.error).toBe("INVALID_MISSION_ID");
        client.disconnect();
        resolve();
      });
    });
  });

  it("broadcasts health, fault, rul, and advisory events to subscribed mission room", async () => {
    const client = Client(`http://localhost:${port}`, {
      auth: { token: generateToken() },
      transports: ["websocket"],
    });

    const missionId = "MSN-BROADCAST-001";
    let receivedEvents = 0;

    await new Promise<void>((resolve) => {
      client.on("connect", () => {
        client.emit("mission:subscribe", missionId);
      });

      client.on("mission:subscribed", () => {
        // Trigger server emissions
        emitHealthUpdated(missionId, { healthScore: 88.0 } as HealthSnapshot);
        emitFaultPredicted(missionId, { faultType: "NONE" } as FaultPrediction);
        emitRulUpdated(missionId, { cycles: 500 } as RulEstimate);
        emitAdvisoryUpdated(missionId, { risk: "LOW", action: "CONTINUE" } as MissionAdvisory);
      });

      client.on("health.updated", (data) => {
        expect(data.healthScore).toBe(88.0);
        receivedEvents++;
        if (receivedEvents === 4) {
          client.disconnect();
          resolve();
        }
      });

      client.on("fault.predicted", (data) => {
        expect(data.faultType).toBe("NONE");
        receivedEvents++;
        if (receivedEvents === 4) {
          client.disconnect();
          resolve();
        }
      });

      client.on("rul.updated", (data) => {
        expect(data.cycles).toBe(500);
        receivedEvents++;
        if (receivedEvents === 4) {
          client.disconnect();
          resolve();
        }
      });

      client.on("advisory.updated", (data) => {
        expect(data.action).toBe("CONTINUE");
        receivedEvents++;
        if (receivedEvents === 4) {
          client.disconnect();
          resolve();
        }
      });
    });
  });
});

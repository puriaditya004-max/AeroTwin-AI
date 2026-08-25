import type { Server as HttpServer } from "http";
import { Server as SocketIOServer } from "socket.io";
import jwt from "jsonwebtoken";
import type { HealthSnapshot, FaultPrediction, RulEstimate, MissionAdvisory } from "../types/contracts";
import type { AuthUser } from "../middleware/auth";

let io: SocketIOServer | undefined;
const JWT_SECRET = process.env.JWT_SECRET ?? "";

export function initSocketServer(httpServer: HttpServer): SocketIOServer {
  io = new SocketIOServer(httpServer, {
    cors: { origin: process.env.CORS_ORIGIN ?? "http://localhost:5173" },
  });

  io.use((socket, next) => {
    const token = socket.handshake.auth?.token as string | undefined;
    if (!token && process.env.NODE_ENV !== "production") {
      next();
      return;
    }
    if (!token) {
      next(new Error("UNAUTHENTICATED"));
      return;
    }
    try {
      socket.data.user = jwt.verify(token, JWT_SECRET) as AuthUser;
      next();
    } catch {
      next(new Error("UNAUTHENTICATED"));
    }
  });

  io.on("connection", (socket) => {
    console.log(`[socket] client connected: ${socket.id}`);

    // Operator HMI joins a room per mission to scope updates.
    socket.on("mission:subscribe", (missionId: string) => {
      if (typeof missionId !== "string" || missionId.trim().length === 0 || missionId.length > 128) {
        socket.emit("mission:error", { error: "INVALID_MISSION_ID" });
        return;
      }
      socket.join(missionRoom(missionId));
    });

    socket.on("mission:unsubscribe", (missionId: string) => {
      if (typeof missionId !== "string" || missionId.trim().length === 0 || missionId.length > 128) return;
      socket.leave(missionRoom(missionId));
    });

    socket.on("disconnect", () => {
      console.log(`[socket] client disconnected: ${socket.id}`);
    });
  });

  return io;
}

function missionRoom(missionId: string): string {
  return `mission:${missionId}`;
}

function getIO(): SocketIOServer {
  if (!io) {
    throw new Error("Socket.IO server not initialized. Call initSocketServer first.");
  }
  return io;
}

export function emitHealthUpdated(missionId: string, snapshot: HealthSnapshot): void {
  getIO().to(missionRoom(missionId)).emit("health.updated", snapshot);
}

export function emitFaultPredicted(missionId: string, prediction: FaultPrediction): void {
  getIO().to(missionRoom(missionId)).emit("fault.predicted", prediction);
}

export function emitRulUpdated(missionId: string, estimate: RulEstimate): void {
  getIO().to(missionRoom(missionId)).emit("rul.updated", estimate);
}

export function emitAdvisoryUpdated(missionId: string, advisory: MissionAdvisory): void {
  getIO().to(missionRoom(missionId)).emit("advisory.updated", advisory);
}

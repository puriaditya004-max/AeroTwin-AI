import { PrismaClient } from "@prisma/client";

// Singleton pattern to avoid exhausting DB connections in dev with hot-reload (tsx watch).
declare global {
  // eslint-disable-next-line no-var
  var __prisma: PrismaClient | undefined;
}

export const prisma: PrismaClient = global.__prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== "production") {
  global.__prisma = prisma;
}

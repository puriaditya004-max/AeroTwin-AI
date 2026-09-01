import { Router } from "express";
import jwt from "jsonwebtoken";
import { prisma } from "../lib/prisma";

import { getJwtSecret } from "../middleware/auth";

export const authRouter = Router();

const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN ?? "1d";

/**
 * ⚠️ DEV-ONLY — POST /auth/dev-login
 *
 * Issues a valid JWT for a seeded dev user with NO password check. Exists
 * purely to unblock testing of requireAuth-protected routes (GET
 * /missions/:id/state, POST /missions, etc.) before a real signup/login
 * flow exists — see "Known gaps" in README.md.
 *
 * Body (optional): { "role": "ADMIN" | "OPERATOR" | "VIEWER" }  (default: OPERATOR)
 *
 * Hard-disabled when NODE_ENV=production so it can never be hit accidentally
 * in a real deployment. MUST be replaced with real authentication before
 * the security-hardening window (24-30h) and before any judge-facing demo.
 */
authRouter.post("/dev-login", async (req, res) => {
  if (process.env.NODE_ENV === "production") {
    res.status(404).json({ error: "NOT_FOUND" });
    return;
  }

  const role = (req.body?.role as string | undefined)?.toUpperCase() ?? "OPERATOR";
  if (!["ADMIN", "OPERATOR", "VIEWER"].includes(role)) {
    res.status(400).json({ error: "INVALID_ROLE", allowed: ["ADMIN", "OPERATOR", "VIEWER"] });
    return;
  }

  const email = `dev-${role.toLowerCase()}@aerotwin.local`;
  const user = await prisma.user.upsert({
    where: { email },
    update: {},
    create: {
      email,
      passwordHash: "dev-only-no-real-password-never-checked",
      role: role as "ADMIN" | "OPERATOR" | "VIEWER",
    },
  });

  const token = jwt.sign(
    { id: user.id, email: user.email, role: user.role },
    getJwtSecret(),
    { expiresIn: JWT_EXPIRES_IN } as jwt.SignOptions
  );

  res.json({ token, user: { id: user.id, email: user.email, role: user.role } });
});
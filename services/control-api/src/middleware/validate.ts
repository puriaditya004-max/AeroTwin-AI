import type { NextFunction, Request, Response } from "express";
import type { ZodTypeAny } from "zod";

/**
 * Generic body validator. On failure, responds 400 with structured issues
 * instead of throwing — callers never need try/catch for this.
 *
 * Usage: router.post("/ingest/health", validateBody(HealthSnapshotSchema), handler)
 */
export function validateBody(schema: ZodTypeAny) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      res.status(400).json({
        error: "VALIDATION_FAILED",
        issues: result.error.issues.map((i) => ({
          path: i.path.join("."),
          message: i.message,
        })),
      });
      return;
    }
    // Replace body with parsed+typed data (applies defaults, strips nothing extra since additionalProperties allowed upstream)
    req.body = result.data;
    next();
  };
}

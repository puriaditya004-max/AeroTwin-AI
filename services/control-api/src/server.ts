import "dotenv/config";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import http from "http";
import { initSocketServer } from "./sockets";
import { healthRouter } from "./routes/health";
import { missionRouter } from "./routes/mission";
import { ingestRouter } from "./routes/ingest";

const app = express();

app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN ?? "http://localhost:5173" }));
app.use(express.json({ limit: "1mb" }));

app.use("/health", healthRouter);
app.use("/missions", missionRouter);
app.use("/ingest", ingestRouter);

// Generic error handler — last middleware. Keeps error messages non-specific
// to avoid leaking internals, per FocusForge's existing security pattern.
app.use((err: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error("[control-api] unhandled error:", err);
  res.status(500).json({ error: "INTERNAL_SERVER_ERROR" });
});

const httpServer = http.createServer(app);
initSocketServer(httpServer);

const PORT = Number(process.env.PORT ?? 4000);

httpServer.listen(PORT, () => {
  console.log(`[control-api] listening on :${PORT}`);
});

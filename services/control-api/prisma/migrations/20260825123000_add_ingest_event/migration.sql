-- Idempotency ledger for upstream module retries.
CREATE TYPE "IngestKind" AS ENUM ('HEALTH', 'FAULT', 'RUL');

CREATE TABLE "ingest_events" (
    "id" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "kind" "IngestKind" NOT NULL,
    "missionId" TEXT NOT NULL,
    "correlationId" TEXT NOT NULL,
    "payloadHash" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ingest_events_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "ingest_events_key_key" ON "ingest_events"("key");
CREATE INDEX "ingest_events_missionId_kind_createdAt_idx" ON "ingest_events"("missionId", "kind", "createdAt");

ALTER TABLE "ingest_events" ADD CONSTRAINT "ingest_events_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "missions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

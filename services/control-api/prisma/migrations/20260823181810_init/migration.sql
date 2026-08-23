-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('ADMIN', 'OPERATOR', 'VIEWER');

-- CreateEnum
CREATE TYPE "MissionStatus" AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'ABORTED');

-- CreateEnum
CREATE TYPE "PredictionKind" AS ENUM ('FAULT', 'RUL');

-- CreateEnum
CREATE TYPE "RiskLevel" AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- CreateEnum
CREATE TYPE "AdvisoryAction" AS ENUM ('CONTINUE', 'REDUCE_LOAD', 'INSPECT');

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "passwordHash" TEXT NOT NULL,
    "role" "UserRole" NOT NULL DEFAULT 'VIEWER',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "engines" (
    "id" TEXT NOT NULL,
    "label" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "engines_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "missions" (
    "id" TEXT NOT NULL,
    "engineId" TEXT NOT NULL,
    "scenarioId" TEXT,
    "status" "MissionStatus" NOT NULL DEFAULT 'PENDING',
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "endedAt" TIMESTAMP(3),

    CONSTRAINT "missions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "twin_snapshots" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "correlationId" TEXT NOT NULL,
    "stateTime" TIMESTAMP(3) NOT NULL,
    "load" DOUBLE PRECISION NOT NULL,
    "stateQuality" TEXT NOT NULL,
    "syncLagMs" DOUBLE PRECISION,
    "raw" JSONB NOT NULL,
    "producerVersion" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "twin_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "health_snapshots" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "correlationId" TEXT NOT NULL,
    "snapshotTime" TIMESTAMP(3) NOT NULL,
    "healthScore" DOUBLE PRECISION NOT NULL,
    "trend" TEXT NOT NULL,
    "violatedRules" TEXT[],
    "reasonCodes" TEXT[],
    "ruleVersion" TEXT NOT NULL,
    "raw" JSONB NOT NULL,
    "producerVersion" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "health_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "predictions" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "correlationId" TEXT NOT NULL,
    "kind" "PredictionKind" NOT NULL,
    "predictionTime" TIMESTAMP(3) NOT NULL,
    "faultType" TEXT,
    "confidence" DOUBLE PRECISION,
    "anomalyScore" DOUBLE PRECISION,
    "cycles" DOUBLE PRECISION,
    "lowerBound" DOUBLE PRECISION,
    "upperBound" DOUBLE PRECISION,
    "rulTrend" TEXT,
    "experimental" BOOLEAN,
    "raw" JSONB NOT NULL,
    "producerVersion" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "predictions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "advisories" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "correlationId" TEXT NOT NULL,
    "advisoryTime" TIMESTAMP(3) NOT NULL,
    "risk" "RiskLevel" NOT NULL,
    "action" "AdvisoryAction" NOT NULL,
    "explanation" TEXT NOT NULL,
    "inspectionRequired" BOOLEAN NOT NULL,
    "raw" JSONB NOT NULL,
    "producerVersion" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "advisories_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_entries" (
    "id" TEXT NOT NULL,
    "missionId" TEXT,
    "userId" TEXT,
    "action" TEXT NOT NULL,
    "detail" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_entries_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "missions_engineId_idx" ON "missions"("engineId");

-- CreateIndex
CREATE INDEX "twin_snapshots_missionId_stateTime_idx" ON "twin_snapshots"("missionId", "stateTime");

-- CreateIndex
CREATE INDEX "health_snapshots_missionId_snapshotTime_idx" ON "health_snapshots"("missionId", "snapshotTime");

-- CreateIndex
CREATE INDEX "predictions_missionId_kind_predictionTime_idx" ON "predictions"("missionId", "kind", "predictionTime");

-- CreateIndex
CREATE INDEX "advisories_missionId_advisoryTime_idx" ON "advisories"("missionId", "advisoryTime");

-- CreateIndex
CREATE INDEX "audit_entries_missionId_idx" ON "audit_entries"("missionId");

-- AddForeignKey
ALTER TABLE "missions" ADD CONSTRAINT "missions_engineId_fkey" FOREIGN KEY ("engineId") REFERENCES "engines"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "twin_snapshots" ADD CONSTRAINT "twin_snapshots_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "missions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "health_snapshots" ADD CONSTRAINT "health_snapshots_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "missions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "predictions" ADD CONSTRAINT "predictions_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "missions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "advisories" ADD CONSTRAINT "advisories_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "missions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_entries" ADD CONSTRAINT "audit_entries_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "missions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_entries" ADD CONSTRAINT "audit_entries_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

/**
 * Seeds the database with a test Engine + Mission that match the IDs used
 * throughout /packages/schemas/samples/*.sample.json (ENG-001,
 * MSN-OILPRESS-001). Run this after every fresh migration so any member can
 * immediately POST sample payloads to /ingest/* without first creating a
 * Mission by hand.
 *
 * Idempotent — safe to re-run (uses upsert).
 *
 * Run manually:  npx prisma db seed
 * Runs automatically in Docker Compose as part of the `migrate` service.
 */
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const engine = await prisma.engine.upsert({
    where: { id: "ENG-001" },
    update: {},
    create: { id: "ENG-001", label: "Seed engine — matches packages/schemas/samples" },
  });

  const mission = await prisma.mission.upsert({
    where: { id: "MSN-OILPRESS-001" },
    update: {},
    create: {
      id: "MSN-OILPRESS-001",
      engineId: engine.id,
      scenarioId: "oil_pressure_degradation",
      status: "RUNNING",
    },
  });

  console.log("Seeded:", { engineId: engine.id, missionId: mission.id });
}

main()
  .catch((err) => {
    console.error("Seed failed:", err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
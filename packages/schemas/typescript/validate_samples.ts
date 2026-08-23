import * as fs from "fs";
import * as path from "path";
import {
  TelemetryFrameSchema,
  TwinStateSchema,
  HealthSnapshotSchema,
  FaultPredictionSchema,
  RulEstimateSchema,
  MissionAdvisorySchema,
} from "./contracts";

const samplesDir = path.join(__dirname, "..", "..", "samples");

const checks: [string, any][] = [
  ["TelemetryFrame", TelemetryFrameSchema],
  ["TwinState", TwinStateSchema],
  ["HealthSnapshot", HealthSnapshotSchema],
  ["FaultPrediction", FaultPredictionSchema],
  ["RulEstimate", RulEstimateSchema],
  ["MissionAdvisory", MissionAdvisorySchema],
];

let allPassed = true;
for (const [name, schema] of checks) {
  const raw = fs.readFileSync(path.join(samplesDir, `${name}.sample.json`), "utf-8");
  const data = JSON.parse(raw);
  const result = schema.safeParse(data);
  if (result.success) {
    console.log(`${name}: VALID (zod)`);
  } else {
    allPassed = false;
    console.log(`${name}: FAILED -> ${JSON.stringify(result.error.issues)}`);
  }
}
process.exit(allPassed ? 0 : 1);

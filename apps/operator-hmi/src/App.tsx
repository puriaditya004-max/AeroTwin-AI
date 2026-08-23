import { useMemo, useState } from "react";
import { TopBar } from "./components/TopBar";
import { RiskBanner } from "./components/RiskBanner";
import { HealthGauge } from "./components/HealthGauge";
import { FaultPanel } from "./components/FaultPanel";
import { RulPanel } from "./components/RulPanel";
import { TelemetryGrid } from "./components/TelemetryGrid";
import { AuditLog } from "./components/AuditLog";
import { useMissionSocket } from "./hooks/useMissionSocket";
import {
  MOCK_MISSION_ID,
  MOCK_ENGINE_ID,
  mockHealth,
  mockFault,
  mockRul,
  mockAdvisory,
  buildMockHistory,
} from "./lib/mockData";

// Toggle this (or wire to a Vite env var) once M3/M4/M5 are producing real
// data end-to-end. Until then DEMO mode lets the dashboard be reviewed and
// used for the backup pitch recording without a live backend.
const MODE: "LIVE" | "DEMO" = (import.meta.env.VITE_HMI_MODE as "LIVE" | "DEMO") ?? "DEMO";

export default function App() {
  const missionId = MOCK_MISSION_ID;
  const engineId = MOCK_ENGINE_ID;

  const live = useMissionSocket(missionId);
  const [advisoryHistory] = useState(() => [mockAdvisory]);
  const history = useMemo(() => buildMockHistory(), []);

  const health = MODE === "LIVE" ? live.health : mockHealth;
  const fault = MODE === "LIVE" ? live.fault : mockFault;
  const advisory = MODE === "LIVE" ? live.advisory : mockAdvisory;
  const rul = MODE === "LIVE" ? undefined : mockRul; // no RUL socket event yet — polled/fetched separately once M5 wires in
  const connected = MODE === "LIVE" ? live.connected : true;

  const currentPoint = history[history.length - 1];

  return (
    <div className="min-h-screen">
      <TopBar engineId={engineId} missionId={missionId} connected={connected} mode={MODE} />

      <main className="mx-auto max-w-6xl space-y-4 px-6 py-6">
        <RiskBanner advisory={advisory} />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[auto_1fr]">
          <div className="panel flex items-center justify-center p-6">
            <HealthGauge score={health?.healthScore ?? 0} trend={health?.trend ?? "STABLE"} />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FaultPanel fault={fault} />
            <RulPanel rul={rul} />
          </div>
        </div>

        <div>
          <div className="eyebrow mb-2">Telemetry</div>
          <TelemetryGrid history={history} current={currentPoint} />
        </div>

        <AuditLog entries={advisoryHistory} />
      </main>
    </div>
  );
}

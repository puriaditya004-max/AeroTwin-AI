import { useEffect, useMemo, useState } from "react";
import { TopBar } from "./components/TopBar";
import { RiskBanner } from "./components/RiskBanner";
import { HealthGauge } from "./components/HealthGauge";
import { FaultPanel } from "./components/FaultPanel";
import { RulPanel } from "./components/RulPanel";
import { TelemetryGrid } from "./components/TelemetryGrid";
import { AuditLog } from "./components/AuditLog";
import { MissionReplay } from "./components/MissionReplay";
import { useMissionSocket } from "./hooks/useMissionSocket";
import {
  MOCK_MISSION_ID,
  MOCK_ENGINE_ID,
  mockHealth,
  mockFault,
  mockRul,
  mockAdvisory,
  mockAdvisoryTimeline,
  buildMockHistory,
} from "./lib/mockData";

// Toggle this (or wire to a Vite env var) once M3/M4/M5 are producing real
// data end-to-end. Until then DEMO mode lets the dashboard be reviewed and
// used for the backup pitch recording without a live backend.
const MODE: "LIVE" | "DEMO" = (import.meta.env.VITE_HMI_MODE as "LIVE" | "DEMO") ?? "DEMO";
const CONTROL_API_URL = import.meta.env.VITE_CONTROL_API_URL ?? "http://localhost:4000";

type View = "live" | "replay";

export default function App() {
  const missionId = MOCK_MISSION_ID;
  const engineId = MOCK_ENGINE_ID;
  const [view, setView] = useState<View>("live");
  const [authToken, setAuthToken] = useState<string | undefined>(() =>
    MODE === "LIVE" ? window.localStorage.getItem("aerotwin.devToken") ?? undefined : undefined
  );
  const [authError, setAuthError] = useState<string | undefined>();

  useEffect(() => {
    if (MODE !== "LIVE" || authToken) return;
    let cancelled = false;

    async function loginForDemo() {
      try {
        const res = await fetch(`${CONTROL_API_URL}/auth/dev-login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: "OPERATOR" }),
        });
        if (!res.ok) {
          throw new Error(`dev-login failed with ${res.status}`);
        }
        const data = (await res.json()) as { token: string };
        if (cancelled) return;
        window.localStorage.setItem("aerotwin.devToken", data.token);
        setAuthToken(data.token);
      } catch (err) {
        if (!cancelled) setAuthError(err instanceof Error ? err.message : "Unable to create dev session");
      }
    }

    loginForDemo();
    return () => {
      cancelled = true;
    };
  }, [authToken]);

  const live = useMissionSocket(missionId, authToken);
  const [advisoryHistory] = useState(() => [mockAdvisory]);
  const history = useMemo(() => buildMockHistory(), []);

  const health = MODE === "LIVE" ? live.health : mockHealth;
  const fault = MODE === "LIVE" ? live.fault : mockFault;
  const rul = MODE === "LIVE" ? live.rul : mockRul;
  const advisory = MODE === "LIVE" ? live.advisory : mockAdvisory;
  const connected = MODE === "LIVE" ? live.connected : true;
  const loadingLive = MODE === "LIVE" && (!authToken || live.loadingInitialState);

  const currentPoint = history[history.length - 1];
  const sensorQuality = MODE === "LIVE" ? undefined : "OK"; // wire to latest TelemetryFrame.qualityFlag once M1/M2 feed is live

  // Replay always uses the golden-demo-journey mock timeline for now — once
  // LIVE mode has an auth token wired in, swap this for a fetch to
  // GET /missions/:id/advisories so replay shows the real recorded mission.
  const replayEntries = mockAdvisoryTimeline;

  return (
    <div className="min-h-screen">
      <TopBar engineId={engineId} missionId={missionId} connected={connected} mode={MODE} />

      <main className="mx-auto max-w-6xl space-y-4 px-6 py-6">
        <div className="flex gap-2">
          <ViewTab label="Live" active={view === "live"} onClick={() => setView("live")} />
          <ViewTab label="Replay" active={view === "replay"} onClick={() => setView("replay")} />
        </div>

        {view === "live" ? (
          <>
            {loadingLive && (
              <div className="panel p-4 text-sm text-text-muted">Connecting to Control API and loading latest mission state...</div>
            )}
            {authError && (
              <div className="panel border-warn/40 p-4 text-sm text-warn">
                Live auth unavailable: {authError}. Demo mode still works for offline review.
              </div>
            )}
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
              <TelemetryGrid history={history} current={currentPoint} qualityFlag={sensorQuality} />
            </div>

            <AuditLog entries={advisoryHistory} />
          </>
        ) : (
          <MissionReplay entries={replayEntries} />
        )}
      </main>
    </div>
  );
}

function ViewTab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`eyebrow rounded px-3 py-1.5 transition-colors ${
        active ? "bg-panel-raised text-text-primary" : "text-text-muted hover:text-text-primary"
      }`}
    >
      {label}
    </button>
  );
}

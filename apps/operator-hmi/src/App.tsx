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
  mockHealth,
  mockFault,
  mockRul,
  mockAdvisory,
  mockAdvisoryTimeline,
  buildMockHistory,
} from "./lib/mockData";

// LIVE uses integrated services. Explicit DEMO is the offline backup.
const MODE: "LIVE" | "DEMO" = (import.meta.env.VITE_HMI_MODE as "LIVE" | "DEMO") ?? "LIVE";
const CONTROL_API_URL = import.meta.env.VITE_CONTROL_API_URL ?? "http://localhost:4000";

const DEFAULT_MISSION_ID = new URLSearchParams(window.location.search).get("missionId") ?? import.meta.env.VITE_DEFAULT_MISSION_ID ?? "MSN-LIVE-001";
const DEFAULT_ENGINE_ID = import.meta.env.VITE_DEFAULT_ENGINE_ID ?? "ENG-001";

type View = "live" | "replay";

export default function App() {
  const [missionId] = useState<string>(DEFAULT_MISSION_ID);
  const [engineId] = useState<string>(DEFAULT_ENGINE_ID);
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
        const res = await fetch(`${CONTROL_API_URL}/auth/demo-login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: "OPERATOR" }),
        });
        if (!res.ok) {
          throw new Error(`Local demo login failed with ${res.status}`);
        }
        const data = (await res.json()) as { token: string };
        if (cancelled) return;
        window.localStorage.setItem("aerotwin.devToken", data.token);
        setAuthError(undefined);
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

  useEffect(() => {
    const expired = () => { window.localStorage.removeItem("aerotwin.devToken"); setAuthToken(undefined); };
    window.addEventListener("aerotwin:auth-expired", expired);
    return () => window.removeEventListener("aerotwin:auth-expired", expired);
  }, []);
  const live = useMissionSocket(missionId, authToken, MODE === "LIVE");
  const demoHistory = useMemo(() => MODE === "DEMO" ? buildMockHistory() : [], []);
  const history = MODE === "LIVE" ? live.history : demoHistory;

  const health = MODE === "LIVE" ? live.health : mockHealth;
  const fault = MODE === "LIVE" ? live.fault : mockFault;
  const rul = MODE === "LIVE" ? live.rul : mockRul;
  const advisory = MODE === "LIVE" ? live.advisory : mockAdvisory;
  const connected = MODE === "LIVE" ? live.connected : true;
  const loadingLive = MODE === "LIVE" && (!authToken || live.loadingInitialState);

  const currentPoint = history[history.length - 1];
  const sensorQuality = MODE === "LIVE" ? live.qualityFlag : "OK";

  const advisoryHistory = MODE === "LIVE" ? live.advisoriesHistory : [mockAdvisory];
  const replayEntries = MODE === "LIVE" ? live.advisoriesHistory : mockAdvisoryTimeline;

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
            {!connected && MODE === "LIVE" && !loadingLive && (
              <div className="panel border-warn/40 bg-warn/10 p-4 text-sm text-warn flex items-center justify-between">
                <span>Disconnected from Control API. Reconnecting...</span>
              </div>
            )}
            {authError && (
              <div className="panel border-warn/40 p-4 text-sm text-warn">
                Live auth unavailable: {authError}. Demo mode still works for offline review.
              </div>
            )}
            {MODE === "LIVE" && live.error && <div className="panel p-4 text-warn">{live.error}</div>}
            <RiskBanner advisory={advisory} />

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[auto_1fr]">
              <div className="panel flex items-center justify-center p-6">
                <HealthGauge score={health?.healthScore} trend={health?.trend} />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FaultPanel fault={fault} />
                <RulPanel rul={rul} />
              </div>
            </div>

            <div>
              <div className="eyebrow mb-2">Telemetry</div>
              <TelemetryGrid history={history} current={currentPoint} qualityFlag={sensorQuality} stateQuality={MODE === "LIVE" ? live.stateQuality : "GOOD"} />
            </div>

            <AuditLog entries={advisoryHistory} />
          </>
        ) : (
          <MissionReplay entries={replayEntries} loading={loadingLive} />
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

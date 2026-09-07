import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import type { HealthSnapshot, FaultPrediction, RulEstimate, MissionAdvisory, TelemetryFrame } from "../types/contracts";
import type { HistoryPoint } from "../components/TelemetryGrid";
const URL = import.meta.env.VITE_CONTROL_API_URL ?? "http://localhost:4000";
export interface LiveMissionData {
  connected: boolean; loadingInitialState: boolean; error?: string;
  health?: HealthSnapshot; fault?: FaultPrediction; rul?: RulEstimate;
  advisory?: MissionAdvisory; advisoriesHistory: MissionAdvisory[];
  history: HistoryPoint[]; qualityFlag?: TelemetryFrame["qualityFlag"]; stateQuality?: string;
}
const empty: LiveMissionData = { connected: false, loadingInitialState: true, advisoriesHistory: [], history: [] };
export function useMissionSocket(missionId: string, authToken?: string, enabled = true): LiveMissionData {
  const [data, setData] = useState<LiveMissionData>(empty);
  useEffect(() => {
    setData(empty);
    if (!enabled || !authToken) return;
    let cancelled = false;
    let busy = false;
    const headers = { Authorization: `Bearer ${authToken}` };
    const base = `${URL}/missions/${encodeURIComponent(missionId)}`;
    const socket = io(URL, { transports: ["websocket"], auth: { token: authToken } });
    async function refresh() {
      if (busy) return;
      busy = true;
      try {
        const responses = await Promise.all(["state", "advisories", "telemetry"].map(path =>
          fetch(`${base}/${path}`, { headers, signal: AbortSignal.timeout(4000) })));
        if (responses.some(r => r.status === 401)) {
          window.dispatchEvent(new Event("aerotwin:auth-expired"));
          return;
        }
        const [state, advisories, telemetry] = await Promise.all(responses.map(r => r.ok ? r.json() : null));
        if (cancelled) return;
        setData(prev => {
          const next = { ...prev, loadingInitialState: false,
            error: responses[0].ok ? undefined : "Mission state unavailable" };
          if (state) {
            for (const [key, time] of [["health", "snapshotTime"], ["fault", "predictionTime"], ["rul", "estimateTime"], ["advisory", "advisoryTime"]] as const) {
              const incoming = state[key];
              const existing = prev[key] as unknown as Record<string, string> | undefined;
              if (incoming && (!existing || Date.parse(incoming[time]) >= Date.parse(existing[time]))) next[key] = incoming;
            }
          }
          if (Array.isArray(advisories)) next.advisoriesHistory = advisories;
          if (telemetry?.sensors) {
            const t = Date.parse(telemetry.stateTime);
            next.history = [...prev.history.filter(p => p.t !== t), { t, ...telemetry.sensors }].sort((a,b) => a.t-b.t).slice(-120);
            next.qualityFlag = telemetry.qualityFlag;
            next.stateQuality = Date.now()-t > 5000 ? "STALE" : telemetry.stateQuality;
          } else { next.stateQuality = "UNAVAILABLE"; }
          return next;
        });
      } catch {
        if (!cancelled) setData(prev => ({ ...prev, loadingInitialState: false, stateQuality: "UNAVAILABLE", error: "Backend connection unavailable" }));
      } finally { busy = false; }
    }
    socket.on("connect", () => { setData(p => ({ ...p, connected: true })); socket.emit("mission:subscribe", missionId); void refresh(); });
    socket.on("disconnect", () => setData(p => ({ ...p, connected: false })));
    socket.on("connect_error", () => setData(p => ({ ...p, connected: false })));
    // Refresh durable snapshots on notifications as well as polling to recover missed events.
    for (const event of ["health.updated", "fault.predicted", "rul.updated", "advisory.updated"]) socket.on(event, () => void refresh());
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => { cancelled = true; window.clearInterval(timer); socket.disconnect(); };
  }, [missionId, authToken, enabled]);
  return data;
}

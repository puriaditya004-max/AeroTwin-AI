import { useEffect, useRef, useState } from "react";
import { io, type Socket } from "socket.io-client";
import type { HealthSnapshot, FaultPrediction, RulEstimate, MissionAdvisory } from "../types/contracts";

const CONTROL_API_URL = import.meta.env.VITE_CONTROL_API_URL ?? "http://localhost:4000";

export interface LiveMissionData {
  connected: boolean;
  loadingInitialState: boolean;
  health?: HealthSnapshot;
  fault?: FaultPrediction;
  rul?: RulEstimate;
  advisory?: MissionAdvisory;
}

interface MissionStateResponse {
  health: HealthSnapshot | null;
  fault: FaultPrediction | null;
  rul: RulEstimate | null;
  advisory: MissionAdvisory | null;
}

/**
 * Subscribes to a mission's realtime events AND fetches the current state via
 * REST on mount. Without the REST fetch, a page refresh mid-mission would show
 * nothing until the next live event arrives — Socket.IO only delivers events
 * that happen after the client subscribes, not history.
 *
 * Requires the caller to pass an auth token, since GET /missions/:id/state
 * is behind requireAuth on the Control API.
 */
export function useMissionSocket(missionId: string, authToken?: string): LiveMissionData {
  const socketRef = useRef<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [loadingInitialState, setLoadingInitialState] = useState(true);
  const [health, setHealth] = useState<HealthSnapshot | undefined>();
  const [fault, setFault] = useState<FaultPrediction | undefined>();
  const [rul, setRul] = useState<RulEstimate | undefined>();
  const [advisory, setAdvisory] = useState<MissionAdvisory | undefined>();

  // Initial REST fetch — runs once per missionId, independent of socket connection.
  useEffect(() => {
    let cancelled = false;

    async function loadInitialState() {
      setLoadingInitialState(true);
      try {
        const res = await fetch(`${CONTROL_API_URL}/missions/${missionId}/state`, {
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
        });
        if (!res.ok) return;
        const data = (await res.json()) as MissionStateResponse;
        if (cancelled) return;
        if (data.health) setHealth(data.health);
        if (data.fault) setFault(data.fault);
        if (data.rul) setRul(data.rul);
        if (data.advisory) setAdvisory(data.advisory);
      } catch (err) {
        console.error("[useMissionSocket] failed to load initial state:", err);
      } finally {
        if (!cancelled) setLoadingInitialState(false);
      }
    }

    loadInitialState();
    return () => {
      cancelled = true;
    };
  }, [missionId, authToken]);

  // Live socket subscription — takes over after initial state is loaded.
  useEffect(() => {
    const socket = io(CONTROL_API_URL, {
      transports: ["websocket"],
      auth: authToken ? { token: authToken } : undefined,
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      setConnected(true);
      socket.emit("mission:subscribe", missionId);
    });

    socket.on("disconnect", () => setConnected(false));
    socket.on("connect_error", (err) => {
      console.error("[useMissionSocket] socket auth/connect failed:", err.message);
      setConnected(false);
    });

    socket.on("health.updated", (payload: HealthSnapshot) => setHealth(payload));
    socket.on("fault.predicted", (payload: FaultPrediction) => setFault(payload));
    socket.on("rul.updated", (payload: RulEstimate) => setRul(payload));
    socket.on("advisory.updated", (payload: MissionAdvisory) => setAdvisory(payload));

    return () => {
      socket.emit("mission:unsubscribe", missionId);
      socket.disconnect();
    };
  }, [missionId]);

  return { connected, loadingInitialState, health, fault, rul, advisory };
}

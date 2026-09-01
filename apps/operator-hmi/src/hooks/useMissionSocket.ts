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
  advisoriesHistory: MissionAdvisory[];
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
 * Re-connects Socket.IO when authToken or missionId changes.
 */
export function useMissionSocket(missionId: string, authToken?: string): LiveMissionData {
  const socketRef = useRef<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [loadingInitialState, setLoadingInitialState] = useState(true);
  const [health, setHealth] = useState<HealthSnapshot | undefined>();
  const [fault, setFault] = useState<FaultPrediction | undefined>();
  const [rul, setRul] = useState<RulEstimate | undefined>();
  const [advisory, setAdvisory] = useState<MissionAdvisory | undefined>();
  const [advisoriesHistory, setAdvisoriesHistory] = useState<MissionAdvisory[]>([]);

  // Reset state on missionId change
  useEffect(() => {
    setHealth(undefined);
    setFault(undefined);
    setRul(undefined);
    setAdvisory(undefined);
    setAdvisoriesHistory([]);
  }, [missionId]);

  // Initial REST fetch for latest state and historical advisories
  useEffect(() => {
    let cancelled = false;

    async function loadInitialState() {
      setLoadingInitialState(true);
      try {
        const headers = authToken ? { Authorization: `Bearer ${authToken}` } : undefined;
        const [stateRes, advRes] = await Promise.allSettled([
          fetch(`${CONTROL_API_URL}/missions/${missionId}/state`, { headers }),
          fetch(`${CONTROL_API_URL}/missions/${missionId}/advisories`, { headers }),
        ]);

        if (cancelled) return;

        if (stateRes.status === "fulfilled" && stateRes.value.ok) {
          const data = (await stateRes.value.json()) as MissionStateResponse;
          if (!cancelled) {
            if (data.health) setHealth(data.health);
            if (data.fault) setFault(data.fault);
            if (data.rul) setRul(data.rul);
            if (data.advisory) setAdvisory(data.advisory);
          }
        }

        if (advRes.status === "fulfilled" && advRes.value.ok) {
          const advData = (await advRes.value.json()) as MissionAdvisory[];
          if (!cancelled && Array.isArray(advData)) {
            setAdvisoriesHistory(advData);
          }
        }
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

  // Live socket subscription
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
    socket.on("advisory.updated", (payload: MissionAdvisory) => {
      setAdvisory(payload);
      setAdvisoriesHistory((prev) => [...prev, payload]);
    });

    return () => {
      socket.emit("mission:unsubscribe", missionId);
      socket.disconnect();
    };
  }, [missionId, authToken]);

  return { connected, loadingInitialState, health, fault, rul, advisory, advisoriesHistory };
}


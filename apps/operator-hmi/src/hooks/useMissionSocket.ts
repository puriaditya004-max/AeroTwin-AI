import { useEffect, useRef, useState } from "react";
import { io, type Socket } from "socket.io-client";
import type { HealthSnapshot, FaultPrediction, MissionAdvisory } from "../types/contracts";

const CONTROL_API_URL = import.meta.env.VITE_CONTROL_API_URL ?? "http://localhost:4000";

export interface LiveMissionData {
  connected: boolean;
  health?: HealthSnapshot;
  fault?: FaultPrediction;
  advisory?: MissionAdvisory;
}

/**
 * Subscribes to a mission's realtime events. Returns the latest value received
 * for each event type. Does NOT fetch initial/historical state — pair with a
 * REST call to /missions/:id/advisories/latest on mount for that.
 */
export function useMissionSocket(missionId: string): LiveMissionData {
  const socketRef = useRef<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [health, setHealth] = useState<HealthSnapshot | undefined>();
  const [fault, setFault] = useState<FaultPrediction | undefined>();
  const [advisory, setAdvisory] = useState<MissionAdvisory | undefined>();

  useEffect(() => {
    const socket = io(CONTROL_API_URL, { transports: ["websocket"] });
    socketRef.current = socket;

    socket.on("connect", () => {
      setConnected(true);
      socket.emit("mission:subscribe", missionId);
    });

    socket.on("disconnect", () => setConnected(false));

    socket.on("health.updated", (payload: HealthSnapshot) => setHealth(payload));
    socket.on("fault.predicted", (payload: FaultPrediction) => setFault(payload));
    socket.on("advisory.updated", (payload: MissionAdvisory) => setAdvisory(payload));

    return () => {
      socket.emit("mission:unsubscribe", missionId);
      socket.disconnect();
    };
  }, [missionId]);

  return { connected, health, fault, advisory };
}

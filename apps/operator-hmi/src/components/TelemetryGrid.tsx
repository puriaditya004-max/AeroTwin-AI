import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";
import type { TelemetryFrame } from "../types/contracts";

interface HistoryPoint {
  t: number;
  rpm: number;
  oilPressureKpa: number;
  oilTempC: number;
  vibrationMmS: number;
}

interface Sensor {
  key: keyof HistoryPoint;
  label: string;
  unit: string;
  current: number;
  color: string;
}

interface TelemetryGridProps {
  history: HistoryPoint[];
  current: HistoryPoint;
  /** Latest TelemetryFrame.qualityFlag, if known. Undefined = unknown/not wired up yet. */
  qualityFlag?: TelemetryFrame["qualityFlag"];
}

export function TelemetryGrid({ history, current, qualityFlag }: TelemetryGridProps) {
  const isDegraded = qualityFlag && qualityFlag !== "OK";

  const sensors: Sensor[] = [
    { key: "rpm", label: "RPM", unit: "rpm", current: current.rpm, color: "#4FD1E8" },
    { key: "oilPressureKpa", label: "Oil Pressure", unit: "kPa", current: current.oilPressureKpa, color: "#FFB020" },
    { key: "oilTempC", label: "Oil Temp", unit: "°C", current: current.oilTempC, color: "#FF4D4D" },
    { key: "vibrationMmS", label: "Vibration", unit: "mm/s", current: current.vibrationMmS, color: "#3DDC84" },
  ];

  return (
    <div>
      {isDegraded && (
        <div className="mb-2 flex items-center gap-2 rounded border border-caution/30 bg-caution/10 px-3 py-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-caution" />
          <span className="eyebrow text-caution">
            sensor data {qualityFlag?.toLowerCase()} — readings below may be stale or estimated
          </span>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {sensors.map((sensor) => (
          <div key={sensor.key} className={`panel p-4 ${isDegraded ? "opacity-60" : ""}`}>
            <div className="eyebrow flex items-center justify-between">
              {sensor.label}
              {isDegraded && <span className="text-caution">⚠</span>}
            </div>
            <div className="mt-1 font-mono text-xl font-medium tabular-nums">
              {sensor.current.toFixed(sensor.key === "rpm" ? 0 : 1)}
              <span className="ml-1 text-xs font-normal text-text-muted">{sensor.unit}</span>
            </div>
            <div className="mt-2 h-10">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history}>
                  <YAxis hide domain={["dataMin", "dataMax"]} />
                  <Line
                    type="monotone"
                    dataKey={sensor.key}
                    stroke={isDegraded ? "#7C8B9B" : sensor.color}
                    strokeWidth={1.5}
                    strokeDasharray={isDegraded ? "3 3" : undefined}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
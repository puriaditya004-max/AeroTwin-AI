import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";

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

export function TelemetryGrid({ history, current }: { history: HistoryPoint[]; current: HistoryPoint }) {
  const sensors: Sensor[] = [
    { key: "rpm", label: "RPM", unit: "rpm", current: current.rpm, color: "#4FD1E8" },
    { key: "oilPressureKpa", label: "Oil Pressure", unit: "kPa", current: current.oilPressureKpa, color: "#FFB020" },
    { key: "oilTempC", label: "Oil Temp", unit: "°C", current: current.oilTempC, color: "#FF4D4D" },
    { key: "vibrationMmS", label: "Vibration", unit: "mm/s", current: current.vibrationMmS, color: "#3DDC84" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {sensors.map((sensor) => (
        <div key={sensor.key} className="panel p-4">
          <div className="eyebrow">{sensor.label}</div>
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
                  stroke={sensor.color}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
    </div>
  );
}

interface HealthGaugeProps {
  score?: number; // 0-100 (undefined = missing/data unavailable)
  trend?: "IMPROVING" | "STABLE" | "DEGRADING";
}

const SIZE = 220;
const STROKE = 14;
const RADIUS = (SIZE - STROKE) / 2;
const CENTER = SIZE / 2;
// Gauge sweeps 220 degrees, from -200deg to +20deg (i.e. mostly the bottom arc),
// like an engine instrument dial rather than a full circle.
const START_ANGLE = -200;
const SWEEP = 220;

function polarToCartesian(angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: CENTER + RADIUS * Math.cos(rad),
    y: CENTER + RADIUS * Math.sin(rad),
  };
}

function arcPath(startDeg: number, endDeg: number) {
  const start = polarToCartesian(startDeg);
  const end = polarToCartesian(endDeg);
  const largeArc = endDeg - startDeg <= 180 ? 0 : 1;
  return `M ${start.x} ${start.y} A ${RADIUS} ${RADIUS} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

function scoreToAngle(score: number) {
  const clamped = Math.max(0, Math.min(100, score));
  return START_ANGLE + (clamped / 100) * SWEEP;
}

function zoneColor(score: number) {
  if (score < 40) return "#FF4D4D"; // warn
  if (score < 70) return "#FFB020"; // caution
  return "#3DDC84"; // safe
}

export function HealthGauge({ score, trend }: HealthGaugeProps) {
  const isAvailable = score !== undefined && !isNaN(score);
  const needleAngle = isAvailable ? scoreToAngle(score) : START_ANGLE + SWEEP / 2;
  const needle = polarToCartesian(needleAngle);
  const color = isAvailable ? zoneColor(score) : "#7C8B9B";

  // Three color zones drawn as separate arc segments (red / amber / green),
  // matching real engine-instrument caution banding.
  const zoneBoundaries = [0, 40, 70, 100].map(scoreToAngle);

  const label = isAvailable
    ? `Health Index · ${trend === "DEGRADING" ? "▼ degrading" : trend === "IMPROVING" ? "▲ improving" : "● stable"}`
    : "Health Index · DATA UNAVAILABLE";

  return (
    <div className="flex flex-col items-center">
      <svg
        width={SIZE}
        height={SIZE * 0.72}
        viewBox={`0 0 ${SIZE} ${SIZE * 0.72}`}
        role="img"
        aria-label={isAvailable ? `Engine health index ${score.toFixed(1)} out of 100, trend ${trend?.toLowerCase()}` : "Engine health data unavailable"}
      >
        {/* Track */}
        <path
          d={arcPath(START_ANGLE, START_ANGLE + SWEEP)}
          fill="none"
          stroke="#1A222C"
          strokeWidth={STROKE}
          strokeLinecap="round"
        />
        {/* Color zones */}
        <path d={arcPath(zoneBoundaries[0], zoneBoundaries[1])} fill="none" stroke="#FF4D4D" strokeOpacity={0.55} strokeWidth={STROKE} strokeLinecap="round" />
        <path d={arcPath(zoneBoundaries[1], zoneBoundaries[2])} fill="none" stroke="#FFB020" strokeOpacity={0.55} strokeWidth={STROKE} />
        <path d={arcPath(zoneBoundaries[2], zoneBoundaries[3])} fill="none" stroke="#3DDC84" strokeOpacity={0.55} strokeWidth={STROKE} strokeLinecap="round" />
        {/* Active value arc */}
        {isAvailable && (
          <path
            d={arcPath(START_ANGLE, needleAngle)}
            fill="none"
            stroke={color}
            strokeWidth={STROKE}
            strokeLinecap="round"
            style={{ transition: "d 0.6s ease" }}
          />
        )}
        {/* Needle */}
        {isAvailable && (
          <>
            <line
              x1={CENTER}
              y1={CENTER}
              x2={needle.x}
              y2={needle.y}
              stroke="#E8EDF2"
              strokeWidth={2}
              style={{ transition: "x2 0.6s ease, y2 0.6s ease" }}
            />
            <circle cx={CENTER} cy={CENTER} r={4} fill="#E8EDF2" />
          </>
        )}
      </svg>
      <div className="-mt-2 text-center">
        <div className="font-mono text-4xl font-medium tabular-nums" style={{ color }}>
          {isAvailable ? score.toFixed(1) : "—"}
        </div>
        <div className="eyebrow mt-1">{label}</div>
      </div>
    </div>
  );
}


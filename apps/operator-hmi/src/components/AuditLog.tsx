import type { MissionAdvisory } from "../types/contracts";

const RISK_DOT: Record<MissionAdvisory["risk"], string> = {
  LOW: "bg-safe",
  MEDIUM: "bg-caution",
  HIGH: "bg-warn",
  CRITICAL: "bg-warn",
};

export function AuditLog({ entries }: { entries: MissionAdvisory[] }) {
  return (
    <div className="panel p-5">
      <div className="eyebrow mb-3">Advisory Trail</div>
      {entries.length === 0 ? (
        <div className="text-sm text-text-muted">No advisories logged yet.</div>
      ) : (
        <ul className="space-y-2">
          {entries.slice().reverse().map((entry, i) => (
            <li key={`${entry.advisoryTime}-${i}`} className="flex items-start gap-3 font-mono text-xs">
              <span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${RISK_DOT[entry.risk]}`} />
              <span className="text-text-muted">{new Date(entry.advisoryTime).toLocaleTimeString()}</span>
              <span className="text-text-primary">
                {entry.risk} → {entry.action.replace("_", " ")}
              </span>
              <span className="truncate text-text-muted">{entry.explanation}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface TopBarProps {
  engineId: string;
  missionId: string;
  connected: boolean;
  mode: "LIVE" | "DEMO";
}

export function TopBar({ engineId, missionId, connected, mode }: TopBarProps) {
  const statusLabel = mode === "DEMO" ? "demo" : connected ? "live" : "disconnected";
  const statusActive = mode === "DEMO" || connected;

  return (
    <header className="flex items-center justify-between border-b border-hairline px-6 py-4">
      <div className="flex items-center gap-3">
        <span className="font-display text-lg font-semibold tracking-tight">AEROTWIN AI</span>
        <span className="text-hairline">|</span>
        <span className="font-mono text-sm text-text-muted">
          {engineId} · {missionId}
        </span>
      </div>
      <div className="flex items-center gap-4">
        {mode === "DEMO" && (
          <span className="eyebrow rounded border border-hairline px-2 py-1 text-data">
            demo data
          </span>
        )}
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${statusActive ? "bg-safe" : "bg-warn"}`}
            style={statusActive ? { boxShadow: "0 0 8px #3DDC84" } : undefined}
          />
          <span className="eyebrow">{statusLabel}</span>
        </div>
      </div>
    </header>
  );
}

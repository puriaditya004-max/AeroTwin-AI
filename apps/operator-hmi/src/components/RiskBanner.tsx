import type { MissionAdvisory } from "../types/contracts";

const RISK_STYLES: Record<MissionAdvisory["risk"], { bg: string; text: string; label: string }> = {
  LOW: { bg: "bg-safe/10 border-safe/30", text: "text-safe", label: "LOW" },
  MEDIUM: { bg: "bg-caution/10 border-caution/30", text: "text-caution", label: "MEDIUM" },
  HIGH: { bg: "bg-warn/10 border-warn/30", text: "text-warn", label: "HIGH" },
  CRITICAL: { bg: "bg-warn/20 border-warn/50", text: "text-warn", label: "CRITICAL" },
};

const ACTION_LABEL: Record<MissionAdvisory["action"], string> = {
  CONTINUE: "Continue",
  REDUCE_LOAD: "Reduce Load",
  INSPECT: "Inspect",
};

export function RiskBanner({ advisory }: { advisory?: MissionAdvisory }) {
  if (!advisory) {
    return (
      <div className="panel flex items-center justify-center p-6 text-text-muted">
        <span className="eyebrow">Waiting for first advisory…</span>
      </div>
    );
  }

  const style = RISK_STYLES[advisory.risk];

  return (
    <div className={`panel border p-6 ${style.bg}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div className="flex items-baseline gap-4">
          <div>
            <div className="eyebrow">Risk</div>
            <div className={`font-display text-3xl font-semibold ${style.text}`}>{style.label}</div>
          </div>
          <div className="h-10 w-px bg-hairline" />
          <div>
            <div className="eyebrow">Recommended action</div>
            <div className="font-display text-3xl font-semibold text-text-primary">
              {ACTION_LABEL[advisory.action]}
            </div>
          </div>
        </div>
        {advisory.inspectionRequired && (
          <span className="eyebrow rounded border border-warn/40 px-2 py-1 text-warn">
            inspection required
          </span>
        )}
      </div>
      <p className="mt-4 max-w-3xl text-sm leading-relaxed text-text-primary/90">{advisory.explanation}</p>
      <p className="mt-3 font-mono text-[11px] text-text-muted">
        {new Date(advisory.advisoryTime).toLocaleTimeString()} · {advisory.producerVersion}
      </p>
    </div>
  );
}

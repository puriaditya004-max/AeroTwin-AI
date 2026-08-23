import type { RulEstimate } from "../types/contracts";

export function RulPanel({ rul }: { rul?: RulEstimate }) {
  return (
    <div className="panel p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="eyebrow">Remaining Useful Life</div>
        <span className="eyebrow rounded border border-hairline px-1.5 py-0.5 text-text-muted">
          experimental
        </span>
      </div>
      {!rul ? (
        <div className="text-sm text-text-muted">No estimate yet</div>
      ) : (
        <>
          <div className="font-mono text-3xl font-medium tabular-nums text-data">
            {rul.cycles.toFixed(0)}
            <span className="ml-2 text-sm font-normal text-text-muted">cycles</span>
          </div>
          <div className="mt-3">
            <div className="mb-1 flex justify-between font-mono text-[11px] text-text-muted">
              <span>{rul.lowerBound.toFixed(0)}</span>
              <span>{rul.upperBound.toFixed(0)}</span>
            </div>
            <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-panel-raised">
              <div
                className="absolute h-full rounded-full bg-data/40"
                style={{
                  left: `${(rul.lowerBound / rul.upperBound) * 20}%`,
                  width: "60%",
                }}
              />
              <div
                className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-data"
                style={{ left: "50%" }}
              />
            </div>
            <div className="mt-1 text-center font-mono text-[10px] text-text-muted">confidence range</div>
          </div>
          <p className="mt-3 text-xs text-text-muted">
            Demonstrator proxy, not field-validated remaining life. Trend: {rul.trend.toLowerCase()}.
          </p>
        </>
      )}
    </div>
  );
}

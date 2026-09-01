import type { FaultPrediction } from "../types/contracts";

export function FaultPanel({ fault }: { fault?: FaultPrediction }) {
  return (
    <div className="panel p-5">
      <div className="eyebrow mb-3">Fault Prediction</div>
      {!fault ? (
        <div className="font-display text-xl text-text-muted">No prediction available</div>
      ) : fault.faultType === "NONE" ? (
        <div className="font-display text-xl text-safe">No fault detected</div>
      ) : (
        <>
          <div className="font-display text-xl font-semibold text-warn">
            {fault.faultType.replace(/_/g, " ")}
          </div>
          <div className="mt-3">
            <div className="mb-1 flex justify-between font-mono text-xs text-text-muted">
              <span>confidence</span>
              <span>{(fault.confidence * 100).toFixed(0)}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel-raised">
              <div
                className="h-full rounded-full bg-warn"
                style={{ width: `${fault.confidence * 100}%` }}
              />
            </div>
          </div>
          {fault.contributors.length > 0 && (
            <div className="mt-4">
              <div className="eyebrow mb-2">Top contributors</div>
              <ul className="space-y-1.5">
                {fault.contributors.slice(0, 3).map((c) => (
                  <li key={c.feature} className="flex items-center justify-between font-mono text-xs">
                    <span className="text-text-muted">{c.feature}</span>
                    <span className={c.contribution >= 0 ? "text-warn" : "text-data"}>
                      {c.contribution >= 0 ? "+" : ""}
                      {c.contribution.toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}

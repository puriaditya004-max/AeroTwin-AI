import { useEffect, useState } from "react";
import type { MissionAdvisory } from "../types/contracts";

const RISK_COLOR: Record<MissionAdvisory["risk"], string> = {
  LOW: "#3DDC84",
  MEDIUM: "#FFB020",
  HIGH: "#FF4D4D",
  CRITICAL: "#FF4D4D",
};

const ACTION_LABEL: Record<MissionAdvisory["action"], string> = {
  CONTINUE: "Continue",
  REDUCE_LOAD: "Reduce Load",
  INSPECT: "Inspect",
};

const PLAYBACK_INTERVAL_MS = 1800;

interface MissionReplayProps {
  entries: MissionAdvisory[];
  /** True while entries are being fetched (LIVE mode) — shows a loading state instead of an empty scrubber. */
  loading?: boolean;
}

/**
 * Scrubbable + auto-playing timeline over a mission's advisory history.
 * Doubles as the pitch demo tool: press play to walk through the "golden
 * demo journey" (normal -> gradual fault -> critical) without touching a
 * live system.
 *
 * DEMO mode source: mockAdvisoryTimeline (packages/schemas doesn't cover
 * this — it's a presentation aid, not a contract).
 * LIVE mode source: intended to be GET /missions/:id/advisories once an
 * auth token is threaded through (see App.tsx comment on authToken) —
 * until then this component just renders whatever `entries` it's given.
 */
export function MissionReplay({ entries, loading }: MissionReplayProps) {
  const [index, setIndex] = useState(entries.length - 1);
  const [playing, setPlaying] = useState(false);

  // Keep the selection valid if entries change size (e.g. LIVE data arrives).
  useEffect(() => {
    setIndex((prev) => Math.min(prev, Math.max(entries.length - 1, 0)));
  }, [entries.length]);

  useEffect(() => {
    if (!playing || entries.length === 0) return;
    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1 >= entries.length ? 0 : prev + 1));
    }, PLAYBACK_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [playing, entries.length]);

  if (loading) {
    return (
      <div className="panel p-5">
        <div className="eyebrow mb-3">Mission Replay</div>
        <div className="text-sm text-text-muted">Loading advisory history…</div>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="panel p-5">
        <div className="eyebrow mb-3">Mission Replay</div>
        <div className="text-sm text-text-muted">No advisory history yet for this mission.</div>
      </div>
    );
  }

  const current = entries[index];
  const signals = current.contributingSignals;

  return (
    <div className="panel p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="eyebrow">Mission Replay</div>
        <span className="font-mono text-[11px] text-text-muted">
          {index + 1} / {entries.length}
        </span>
      </div>

      {/* Selected snapshot */}
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3 rounded border border-hairline bg-panel-raised p-4">
        <div className="flex items-baseline gap-4">
          <div>
            <div className="eyebrow">Risk</div>
            <div className="font-display text-2xl font-semibold" style={{ color: RISK_COLOR[current.risk] }}>
              {current.risk}
            </div>
          </div>
          <div className="h-8 w-px bg-hairline" />
          <div>
            <div className="eyebrow">Action</div>
            <div className="font-display text-2xl font-semibold text-text-primary">
              {ACTION_LABEL[current.action]}
            </div>
          </div>
        </div>
        <div className="font-mono text-xs text-text-muted">
          {new Date(current.advisoryTime).toLocaleTimeString()}
        </div>
      </div>

      <p className="mb-4 text-sm leading-relaxed text-text-primary/90">{current.explanation}</p>

      {signals && (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <ReplayStat label="Health" value={signals.healthScore?.toFixed(1) ?? "—"} />
          <ReplayStat label="Fault" value={signals.faultType === "NONE" || !signals.faultType ? "None" : signals.faultType.replace(/_/g, " ")} />
          <ReplayStat
            label="Confidence"
            value={signals.faultConfidence !== undefined ? `${(signals.faultConfidence * 100).toFixed(0)}%` : "—"}
          />
          <ReplayStat label="RUL" value={signals.rulCycles !== undefined ? `${signals.rulCycles.toFixed(0)} cyc` : "—"} />
        </div>
      )}

      {/* Scrubber */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setPlaying((p) => !p)}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-hairline text-text-primary hover:bg-panel-raised"
          aria-label={playing ? "Pause replay" : "Play replay"}
        >
          {playing ? "❚❚" : "▶"}
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(entries.length - 1, 0)}
          value={index}
          onChange={(e) => {
            setPlaying(false);
            setIndex(Number(e.target.value));
          }}
          className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-panel-raised accent-data"
        />
      </div>

      {/* Timeline ticks — one dot per entry, colored by risk, for a visual scan of the whole mission */}
      <div className="mt-2 flex items-center gap-1">
        {entries.map((entry, i) => (
          <button
            key={`${entry.advisoryTime}-${i}`}
            onClick={() => {
              setPlaying(false);
              setIndex(i);
            }}
            className="h-1.5 flex-1 rounded-full transition-opacity"
            style={{
              backgroundColor: RISK_COLOR[entry.risk],
              opacity: i === index ? 1 : 0.3,
            }}
            aria-label={`Jump to advisory ${i + 1} of ${entries.length}`}
          />
        ))}
      </div>
    </div>
  );
}

function ReplayStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-hairline p-2.5">
      <div className="eyebrow">{label}</div>
      <div className="mt-0.5 font-mono text-sm font-medium">{value}</div>
    </div>
  );
}
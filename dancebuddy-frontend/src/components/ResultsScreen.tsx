import { useEffect, useRef, useState } from "react";
import type { AnalyzeResult } from "../api";
import { mediaUrl } from "../api";
import { ChevronDown, ChevronLeft, ChevronRight, PauseIcon, PlayIcon, RefreshIcon } from "../icons";
import { CONNECTION_LABELS } from "../skeleton";
import { VideoWithOverlay } from "./VideoWithOverlay";

const VERDICT: Record<string, [string, string]> = {
  far: ["Far off", "text-diverge"],
  somewhat_similar: ["Somewhat similar", "text-amber-400"],
  quite_similar: ["Quite similar", "text-match"],
  very_similar: ["Very similar", "text-emerald-400"],
};

function Legend() {
  return (
    <div className="flex items-center gap-3 text-[11px] text-muted">
      <span className="flex items-center gap-1">
        <span className="h-1 w-3 rounded bg-diverge" />off
      </span>
      <span className="flex items-center gap-1">
        <span className="h-1 w-3 rounded bg-match" />match
      </span>
    </div>
  );
}

interface Props {
  result: AnalyzeResult;
  onReset: () => void;
}

export function ResultsScreen({ result, onReset }: Props) {
  const subject = result.subjects[0];
  const frames = subject?.frame_pairs ?? [];
  const total = frames.length;

  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [showScore, setShowScore] = useState(false);
  const userElRef = useRef<HTMLVideoElement | null>(null);
  const refElRef = useRef<HTMLVideoElement | null>(null);
  const indexRef = useRef(index);
  indexRef.current = index;
  const clamp = (i: number) => Math.max(0, Math.min(total - 1, i));

  // Advance frames on a wall clock (independent of any video), so the overlay and frame bar
  // never freeze even if a video stalls. Both videos also play natively alongside for smooth
  // footage; the sync keeps them at a constant time offset, so real-time playback stays aligned.
  useEffect(() => {
    if (!playing) return;
    if (total <= 1) {
      setPlaying(false);
      return;
    }
    const u = userElRef.current;
    const r = refElRef.current;

    let start = indexRef.current;
    if (start >= total - 1) {
      start = 0;
      setIndex(0);
    }
    const startTs = frames[start].user.timestamp;
    const startWall = performance.now();
    try {
      if (u) u.currentTime = frames[start].user.timestamp;
      if (r) r.currentTime = frames[start].reference.timestamp;
    } catch {
      /* metadata not ready */
    }
    void u?.play().catch(() => {});
    void r?.play().catch(() => {});

    let raf = 0;
    const tick = () => {
      const t = startTs + (performance.now() - startWall) / 1000;
      let k = indexRef.current;
      while (k < total - 1 && frames[k + 1].user.timestamp <= t) k++;
      if (k !== indexRef.current) setIndex(k);
      if (k >= total - 1) {
        setPlaying(false);
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      u?.pause();
      r?.pause();
    };
  }, [playing, total, frames]);

  // fetch each clip as a blob → same-origin blob URL (cross-origin <video> won't load)
  const [userSrc, setUserSrc] = useState("");
  const [refSrc, setRefSrc] = useState("");
  useEffect(() => {
    let cancelled = false;
    const created: string[] = [];
    setUserSrc("");
    setRefSrc("");
    (async () => {
      try {
        const [ub, rb] = await Promise.all([
          fetch(mediaUrl(result.user.playback_url)).then((r) => r.blob()),
          fetch(mediaUrl(result.reference.playback_url)).then((r) => r.blob()),
        ]);
        if (cancelled) return;
        const u = URL.createObjectURL(ub);
        const rr = URL.createObjectURL(rb);
        created.push(u, rr);
        setUserSrc(u);
        setRefSrc(rr);
      } catch {
        /* videos stay blank */
      }
    })();
    return () => {
      cancelled = true;
      created.forEach(URL.revokeObjectURL);
    };
  }, [result]);

  if (!subject || total === 0) {
    return (
      <div className="mx-auto max-w-md px-5 py-20 text-center">
        <p className="text-fg">No overlapping frames were found between the two videos.</p>
        <button
          onClick={onReset}
          className="mt-4 cursor-pointer rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-strong"
        >
          Try again
        </button>
      </div>
    );
  }

  const current = frames[index];
  const score = Math.round(subject.score);
  const [vLabel, vColor] = VERDICT[subject.verdict] ?? [subject.verdict, "text-fg"];
  const breakdown = subject.breakdown ?? [];
  const offLabels = Array.from(
    new Set(current.error_connections.map((id) => CONNECTION_LABELS[id] ?? id)),
  );

  const iconBtn =
    "flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface-2 hover:text-fg disabled:opacity-35 disabled:hover:bg-transparent cursor-pointer";
  const ghostBtn =
    "flex cursor-pointer items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-surface-2 hover:text-fg";

  return (
    <section className="mx-auto w-full max-w-6xl px-5 py-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <VideoWithOverlay
          videoUrl={userSrc}
          side={current.user}
          errorConnections={current.error_connections}
          label="Your video"
          isPlaying={playing}
          videoElRef={userElRef}
        />
        <VideoWithOverlay
          videoUrl={refSrc}
          side={current.reference}
          errorConnections={current.error_connections}
          label="Reference"
          isPlaying={playing}
          videoElRef={refElRef}
        />
      </div>

      {/* per-frame readout */}
      <p className="mt-3 h-4 text-center text-xs text-muted">
        {offLabels.length ? (
          <>
            <span className="text-diverge">Off:</span> {offLabels.join(", ")}
          </>
        ) : (
          "Limbs in sync"
        )}
      </p>

      {/* discreet bottom bar: legend (always shown) + transport + score/new */}
      <div className="relative mt-3 flex items-center gap-3 rounded-xl border border-line/70 bg-surface/50 px-3 py-2">
        <Legend />

        <button
          className={iconBtn}
          onClick={() => {
            setPlaying(false);
            setIndex((i) => clamp(i - 1));
          }}
          disabled={index === 0}
          aria-label="Previous frame"
        >
          <ChevronLeft width={18} height={18} />
        </button>
        <button
          className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-brand/15 text-brand transition-colors hover:bg-brand/25"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? <PauseIcon width={16} height={16} /> : <PlayIcon width={16} height={16} />}
        </button>
        <button
          className={iconBtn}
          onClick={() => {
            setPlaying(false);
            setIndex((i) => clamp(i + 1));
          }}
          disabled={index >= total - 1}
          aria-label="Next frame"
        >
          <ChevronRight width={18} height={18} />
        </button>

        <input
          type="range"
          min={0}
          max={Math.max(0, total - 1)}
          value={index}
          onChange={(e) => {
            setPlaying(false);
            setIndex(clamp(Number(e.target.value)));
          }}
          className="mx-1 h-1 flex-1 cursor-pointer rounded-full bg-surface-2"
          style={{ accentColor: "var(--color-brand)" }}
          aria-label="Scrub through frames"
        />
        <span className="min-w-[64px] text-right text-xs tabular-nums text-muted">
          {index + 1} / {total}
        </span>

        <button
          className={`${ghostBtn} ${showScore ? "bg-surface-2 text-fg" : ""}`}
          onClick={() => setShowScore((s) => !s)}
          aria-expanded={showScore}
        >
          Score
          <ChevronDown
            width={13}
            height={13}
            className={`transition-transform ${showScore ? "rotate-180" : ""}`}
          />
        </button>
        <button onClick={onReset} className={ghostBtn}>
          <RefreshIcon width={14} height={14} /> New
        </button>

        {/* score popover */}
        {showScore && (
          <div className="absolute bottom-full right-2 z-10 mb-2 w-64 rounded-xl border border-line bg-surface p-4 shadow-2xl">
            <div className="flex items-baseline gap-1.5">
              <span className={`text-2xl font-bold tracking-tight tabular-nums ${vColor}`}>
                {score}
              </span>
              <span className="text-xs text-muted">/100</span>
            </div>
            <p className={`mt-1 text-sm font-medium ${vColor}`}>{vLabel}</p>

            <p className="mt-3 text-[11px] uppercase tracking-wide text-muted">Most different</p>
            {breakdown.length === 0 ? (
              <p className="mt-1 text-xs text-fg">Nothing notably off — great match.</p>
            ) : (
              <div className="mt-1.5 flex flex-col gap-2">
                {breakdown.map(({ area, pct }) => (
                  <div key={area}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="capitalize text-fg">{area}</span>
                      <span className="tabular-nums text-muted">{pct}%</span>
                    </div>
                    <div className="mt-0.5 h-1 w-full overflow-hidden rounded-full bg-surface-2">
                      <div
                        className="h-full rounded-full bg-diverge"
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

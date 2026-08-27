import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import type { Side } from "../api";
import { contentRect, drawSkeleton } from "../skeleton";

// Fixed box shape so landscape and portrait clips letterbox into a uniform grid.
const BOX_ASPECT = 4 / 3;

interface Props {
  videoUrl: string;
  side: Side;
  errorConnections: string[];
  label: string;
  isPlaying: boolean;
  videoElRef?: RefObject<HTMLVideoElement | null>;
}

export function VideoWithOverlay({
  videoUrl,
  side,
  errorConnections,
  label,
  isPlaying,
  videoElRef,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const [videoAspect, setVideoAspect] = useState(0);

  // Expose the underlying <video> to the parent so it can drive native playback.
  useEffect(() => {
    if (videoElRef) videoElRef.current = videoRef.current;
    return () => {
      if (videoElRef) videoElRef.current = null;
    };
  }, [videoElRef]);

  // Release the video's decoder on unmount so Chrome reclaims it between analyses (its decoder
  // pool is limited, and it's slow to free them otherwise).
  useEffect(() => {
    const v = videoRef.current;
    return () => {
      if (!v) return;
      try {
        v.pause();
        v.removeAttribute("src");
        v.load();
      } catch {
        /* ignore */
      }
    };
  }, []);

  // Seek to this frame's timestamp only when paused. During playback the parent lets the
  // video play natively, so seeking here would fight it.
  useEffect(() => {
    if (isPlaying) return;
    const v = videoRef.current;
    if (v && Number.isFinite(side.timestamp)) {
      try {
        v.currentTime = side.timestamp;
      } catch {
        /* metadata not ready yet */
      }
    }
  }, [side.timestamp, isPlaying]);

  // Draw the skeleton into the video's letterboxed area, redrawing on resize.
  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    const box = boxRef.current;
    if (!canvas || !box) return;

    const render = () => {
      const w = box.clientWidth;
      const h = box.clientHeight;
      if (!w || !h) return;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const rect = contentRect(w, h, videoAspect);
      drawSkeleton(ctx, side.keypoints, errorConnections, w, h, rect);
    };

    render();
    const ro = new ResizeObserver(render);
    ro.observe(box);
    return () => ro.disconnect();
  }, [side, errorConnections, videoAspect]);

  return (
    <figure className="min-w-0">
      <figcaption className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
        {label}
      </figcaption>
      <div
        ref={boxRef}
        className="relative w-full overflow-hidden rounded-xl border border-line bg-black"
        style={{ aspectRatio: String(BOX_ASPECT) }}
      >
        <video
          ref={videoRef}
          src={videoUrl || undefined}
          muted
          playsInline
          preload="auto"
          onLoadedMetadata={(e) => {
            const v = e.currentTarget;
            if (v.videoWidth && v.videoHeight) setVideoAspect(v.videoWidth / v.videoHeight);
          }}
          className="absolute inset-0 h-full w-full object-contain"
        />
        <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" />
      </div>
    </figure>
  );
}

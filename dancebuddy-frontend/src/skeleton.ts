// 17-joint COCO skeleton (matches the backend) and canvas draw helpers.

import type { Keypoint } from "./api";

// [id, startIndex, endIndex] for the 13 scored limb segments.
export const CONNECTIONS: [string, number, number][] = [
  ["nose_l_eye", 0, 1],
  ["nose_r_eye", 0, 2],
  ["l_eye_ear", 1, 3],
  ["r_eye_ear", 2, 4],
  ["shoulders", 5, 6],
  ["l_upper_arm", 5, 7],
  ["r_upper_arm", 6, 8],
  ["l_forearm", 7, 9],
  ["r_forearm", 8, 10],
  ["l_thigh", 11, 13],
  ["r_thigh", 12, 14],
  ["l_shin", 13, 15],
  ["r_shin", 14, 16],
];

// Readable names for the per-limb display.
export const CONNECTION_LABELS: Record<string, string> = {
  nose_l_eye: "head (left)",
  nose_r_eye: "head (right)",
  l_eye_ear: "head (left)",
  r_eye_ear: "head (right)",
  shoulders: "shoulders",
  l_upper_arm: "left upper arm",
  r_upper_arm: "right upper arm",
  l_forearm: "left forearm",
  r_forearm: "right forearm",
  l_thigh: "left thigh",
  r_thigh: "right thigh",
  l_shin: "left shin",
  r_shin: "right shin",
};

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

const MIN_CONF = 0.3;
const COLOR_MATCH = "#22d3ee";
const COLOR_DIVERGE = "#ef4444";
const COLOR_JOINT = "#e5e7eb";

/** Draw one skeleton into `rect` (the video's letterboxed content area within the canvas). */
export function drawSkeleton(
  ctx: CanvasRenderingContext2D,
  keypoints: Keypoint[] | null,
  errorConnections: string[],
  canvasW: number,
  canvasH: number,
  rect: Rect,
): void {
  ctx.clearRect(0, 0, canvasW, canvasH);
  if (!keypoints) return;

  const px = (k: Keypoint): [number, number] => [rect.x + k[0] * rect.w, rect.y + k[1] * rect.h];
  const errors = new Set(errorConnections);
  const lineWidth = Math.max(2, Math.round(Math.min(rect.w, rect.h) * 0.009));
  ctx.lineCap = "round";

  for (const [id, a, b] of CONNECTIONS) {
    const ka = keypoints[a];
    const kb = keypoints[b];
    if (!ka || !kb || ka[2] < MIN_CONF || kb[2] < MIN_CONF) continue;
    const diverges = errors.has(id);
    const [ax, ay] = px(ka);
    const [bx, by] = px(kb);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.strokeStyle = diverges ? COLOR_DIVERGE : COLOR_MATCH;
    ctx.lineWidth = lineWidth;
    ctx.shadowColor = diverges ? "rgba(239,68,68,0.55)" : "rgba(34,211,238,0.5)";
    ctx.shadowBlur = lineWidth * 1.5;
    ctx.stroke();
  }

  ctx.shadowBlur = 0;
  const r = Math.max(2, Math.round(Math.min(rect.w, rect.h) * 0.006));
  for (const k of keypoints) {
    if (k[2] < MIN_CONF) continue;
    const [x, y] = px(k);
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = COLOR_JOINT;
    ctx.fill();
  }
}

/** Compute the letterboxed content rect of a video (intrinsic aspect) inside a box. */
export function contentRect(boxW: number, boxH: number, videoAspect: number): Rect {
  if (!videoAspect || !boxW || !boxH) return { x: 0, y: 0, w: boxW, h: boxH };
  const boxAspect = boxW / boxH;
  if (videoAspect > boxAspect) {
    const w = boxW;
    const h = boxW / videoAspect;
    return { x: 0, y: (boxH - h) / 2, w, h };
  }
  const h = boxH;
  const w = boxH * videoAspect;
  return { x: (boxW - w) / 2, y: 0, w, h };
}

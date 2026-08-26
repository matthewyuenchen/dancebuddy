// Client for the analyze endpoint.

export type Keypoint = [number, number, number]; // [x, y, confidence], x/y normalized 0..1

export interface Side {
  source_frame: number;
  timestamp: number;
  keypoints: Keypoint[] | null;
}

export interface FramePair {
  index: number;
  user: Side;
  reference: Side;
  error_connections: string[]; // individual diverging limbs (drawn red)
}

export interface AreaScore {
  area: string;
  pct: number; // % of visible frames this body area diverged
}

export interface Subject {
  subject_id: number;
  role: string;
  score: number;
  verdict: string;
  breakdown: AreaScore[];
  frame_pairs: FramePair[];
}

export interface VideoMeta {
  fps: number;
  frame_count: number;
  duration_sec: number;
  width: number;
  height: number;
  playback_url: string; // path to the transcoded, browser-playable mp4 (served by the API)
}

export interface AnalyzeResult {
  schema_version: string;
  status: "completed";
  level: string;
  reference: VideoMeta;
  user: VideoMeta;
  subjects: Subject[];
}

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

/** Turn a backend-relative media path into an absolute URL the browser can load. */
export function mediaUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_URL}${path}`;
}

export async function analyzeVideos(userFile: File, referenceFile: File): Promise<AnalyzeResult> {
  const form = new FormData();
  form.append("user_video", userFile);
  form.append("reference_video", referenceFile);

  let res: Response;
  try {
    res = await fetch(`${API_URL}/analyze`, { method: "POST", body: form });
  } catch {
    throw new Error(`Couldn't reach the analysis server at ${API_URL}. Make sure the backend is running.`);
  }

  const data = await res.json().catch(() => null);
  if (!res.ok || !data || data.status === "error") {
    throw new Error(data?.error?.message ?? `Analysis failed (HTTP ${res.status}).`);
  }
  return data as AnalyzeResult;
}

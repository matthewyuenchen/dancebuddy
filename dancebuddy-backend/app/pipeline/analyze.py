"""Top-level analysis: pose estimation, time alignment, comparison and scoring for two
videos, assembled into a JSON-serializable result."""

from __future__ import annotations

from app.pipeline import compare, score, sync
from app.pipeline.adapters.base import PoseAdapter, VideoPoses
from app.pipeline.adapters.yolo_adapter import YoloAdapter
from app.pipeline.canonical import BODY_AREA_BY_CONNECTION, Person, primary_person

SCHEMA_VERSION = "1.0"


def analyze(
    user_video: str,
    reference_video: str,
    level: str = "high",
    adapter: PoseAdapter | None = None,
) -> dict:
    """Analyze two videos and return the result dict. `adapter` defaults to YOLO-pose;
    `level` sets comparison strictness."""
    if level not in compare.LEVEL_THRESHOLDS_DEG:
        raise ValueError(f"unknown level: {level!r}")
    adapter = adapter or YoloAdapter()

    user = adapter.estimate_video(user_video)
    reference = adapter.estimate_video(reference_video)
    au, ar = user.aspect, reference.aspect

    aligned = sync.align(user, reference)

    frame_pairs: list[dict] = []
    per_frame: list[tuple[int, int]] = []
    div_count: dict[str, int] = {}
    eval_count: dict[str, int] = {}
    for i, pair in enumerate(aligned):
        user_person = primary_person(user.frames[pair.user_frame])
        ref_person = primary_person(reference.frames[pair.reference_frame])

        if user_person is not None and ref_person is not None:
            diverging, evaluated = compare.evaluate_people(user_person, ref_person, level, au, ar)
        else:
            diverging, evaluated = [], []
        per_frame.append((len(diverging), len(evaluated)))
        for c in evaluated:
            eval_count[c] = eval_count.get(c, 0) + 1
        for c in diverging:
            div_count[c] = div_count.get(c, 0) + 1

        frame_pairs.append(
            {
                "index": i,
                "user": _frame_side(user_person, pair.user_frame, user),
                "reference": _frame_side(ref_person, pair.reference_frame, reference),
                "error_connections": diverging,
            }
        )

    total = score.score_from_frames(per_frame)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "level": level,
        "reference": _video_meta(reference),
        "user": _video_meta(user),
        "subjects": [
            {
                "subject_id": 0,
                "role": "primary",
                "score": total,
                "verdict": score.verdict_for(total),
                "breakdown": _area_breakdown(div_count, eval_count),
                "frame_pairs": frame_pairs,
            }
        ],
    }


def _area_breakdown(div_count: dict[str, int], eval_count: dict[str, int]) -> list[dict]:
    """For each body area, the percentage of visible frames in which it diverged, most first."""
    area_div: dict[str, int] = {}
    area_eval: dict[str, int] = {}
    for conn, cnt in eval_count.items():
        area = BODY_AREA_BY_CONNECTION.get(conn, conn)
        area_eval[area] = area_eval.get(area, 0) + cnt
    for conn, cnt in div_count.items():
        area = BODY_AREA_BY_CONNECTION.get(conn, conn)
        area_div[area] = area_div.get(area, 0) + cnt

    rows = [
        {"area": area, "pct": round(100.0 * area_div.get(area, 0) / evaluated, 1)}
        for area, evaluated in area_eval.items()
        if evaluated > 0
    ]
    rows.sort(key=lambda r: r["pct"], reverse=True)
    return rows


def _serialize(person: Person | None):
    return [[k.x, k.y, k.confidence] for k in person] if person is not None else None


def _frame_side(person: Person | None, analyzed_index: int, poses: VideoPoses) -> dict:
    source_frame = analyzed_index * poses.frame_interval
    timestamp = source_frame / poses.fps if poses.fps else 0.0
    return {
        "source_frame": source_frame,
        "timestamp": round(timestamp, 3),
        "keypoints": _serialize(person),
    }


def _video_meta(poses: VideoPoses) -> dict:
    original_frames = poses.frame_count * poses.frame_interval
    duration = original_frames / poses.fps if poses.fps else 0.0
    return {
        "fps": round(poses.fps, 3),
        "frame_count": poses.frame_count,
        "duration_sec": round(duration, 3),
        "width": poses.width,
        "height": poses.height,
    }

"""Pipeline logic tests on synthetic poses (no YOLO/torch/video): comparison, per-limb
scoring, sync, and analyze() end-to-end via a FakeAdapter."""

from __future__ import annotations

import pytest

from app.pipeline import analyze, canonical, compare, score, sync
from app.pipeline.adapters.base import PoseAdapter, VideoPoses
from app.pipeline.canonical import Keypoint

from app.pipeline.adapters import yolo_adapter  # noqa: F401  (imports without torch)

# A plausible standing figure, normalized [0,1], index == COCO joint.
_STANDING = {
    0: (0.50, 0.10), 1: (0.48, 0.08), 2: (0.52, 0.08), 3: (0.46, 0.09), 4: (0.54, 0.09),
    5: (0.45, 0.25), 6: (0.55, 0.25), 7: (0.42, 0.35), 8: (0.58, 0.35),
    9: (0.40, 0.45), 10: (0.60, 0.45), 11: (0.47, 0.50), 12: (0.53, 0.50),
    13: (0.46, 0.70), 14: (0.54, 0.70), 15: (0.46, 0.90), 16: (0.54, 0.90),
}


def make_person(overrides: dict[int, tuple[float, float]] | None = None):
    coords = dict(_STANDING)
    if overrides:
        coords.update(overrides)
    return [Keypoint(coords[i][0], coords[i][1], 1.0) for i in range(17)]


class FakeAdapter(PoseAdapter):
    def __init__(self, videos: dict[str, VideoPoses]):
        self._videos = videos

    def estimate_video(self, video_path: str) -> VideoPoses:
        return self._videos[video_path]


# --- schema -----------------------------------------------------------------
def test_schema_shape():
    assert canonical.NUM_KEYPOINTS == 17 == len(canonical.KEYPOINT_NAMES)
    assert len(canonical.CONNECTIONS) == 13


# --- compare ----------------------------------------------------------------
def test_identical_people_no_divergence():
    p = make_person()
    diverging, evaluated = compare.evaluate_people(p, p, "high")
    assert diverging == []
    assert len(evaluated) == 13  # all limbs visible + judged


def test_bent_forearm_flagged():
    ref = make_person()
    user = make_person({9: (0.52, 0.35)})  # swing left wrist out
    assert "l_forearm" in compare.compare_people(user, ref, "high")


def test_low_confidence_limb_excluded():
    ref = make_person()
    user = make_person({9: (0.52, 0.35)})
    user[9] = Keypoint(user[9].x, user[9].y, 0.0)  # wrist unseen
    diverging, evaluated = compare.evaluate_people(user, ref, "high")
    assert "l_forearm" not in diverging
    assert "l_forearm" not in evaluated  # excluded, not counted as a match


def test_aspect_changes_angle():
    a = Keypoint(0.4, 0.4, 1.0)
    b = Keypoint(0.5, 0.5, 1.0)  # dx=dy=0.1
    assert compare.segment_angle_deg(a, b, 1.0) == pytest.approx(45.0)
    # widening the horizontal axis rotates the measured angle toward horizontal
    assert compare.segment_angle_deg(a, b, 2.0) == pytest.approx(26.565, abs=0.01)


def test_frame_distance_identical_is_zero():
    p = make_person()
    assert compare.frame_distance(p, p) == 0.0


# --- score (per-limb) -------------------------------------------------------
def test_perfect_match_scores_100():
    assert score.score_from_frames([(0, 13), (0, 13), (0, 13)]) == 100.0


def test_all_wrong_scores_0():
    assert score.score_from_frames([(13, 13)]) == 0.0


def test_partial_score():
    # matching = (5-0)+(10-2) = 13, evaluated = 15 -> 86.7
    assert score.score_from_frames([(0, 5), (2, 10)]) == 86.7


def test_no_evaluated_scores_0():
    assert score.score_from_frames([(0, 0), (0, 0)]) == 0.0


# --- sync (trims dead frames, then aligns) ----------------------------------
def test_sync_trims_and_aligns():
    A = make_person()
    B = make_person({9: (0.52, 0.35)})
    C = make_person({10: (0.48, 0.35)})
    # reference has 2 empty (no-dancer) lead-in frames, then A,B,C
    reference = VideoPoses(30.0, 5, [[], [], [A], [B], [C]], 1)
    user = VideoPoses(30.0, 3, [[A], [B], [C]], 1)
    pairs = sync.align(user, reference)
    # lead-in trimmed; user frame k aligns to reference frame k+2
    assert [(p.user_frame, p.reference_frame) for p in pairs] == [(0, 2), (1, 3), (2, 4)]


# --- analyze end-to-end (FakeAdapter) ---------------------------------------
def test_analyze_identical_videos():
    frames = [[make_person()] for _ in range(6)]
    poses = VideoPoses(fps=30.0, frame_count=6, frames=frames, frame_interval=3)
    adapter = FakeAdapter({"u.mp4": poses, "r.mp4": poses})

    result = analyze.analyze("u.mp4", "r.mp4", level="high", adapter=adapter)

    subject = result["subjects"][0]
    assert subject["score"] == 100.0
    assert subject["verdict"] == "very_similar"
    fp = subject["frame_pairs"][0]
    assert fp["error_connections"] == []
    assert len(fp["user"]["keypoints"]) == 17
    assert subject["frame_pairs"][1]["user"]["source_frame"] == 3
    assert subject["frame_pairs"][1]["user"]["timestamp"] == 0.1


def test_analyze_rejects_unknown_level():
    poses = VideoPoses(30.0, 1, [[make_person()]], 3)
    adapter = FakeAdapter({"u.mp4": poses, "r.mp4": poses})
    with pytest.raises(ValueError):
        analyze.analyze("u.mp4", "r.mp4", level="ultra", adapter=adapter)

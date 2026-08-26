"""Time-align two clips: trim dead lead-in/out, find the consecutive-frame window where the
two performances best match (the anchor), then pair frames outward scaled by the fps ratio."""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline import compare
from app.pipeline.adapters.base import VideoPoses
from app.pipeline.canonical import FramePose, Person, primary_person

WINDOW = 8
_MAX_COST = 180.0
_MIN_VISIBLE_JOINTS = 6


@dataclass(frozen=True)
class AlignedPair:
    """A time-aligned frame pair (indices into analyzed frames)."""
    user_frame: int
    reference_frame: int


def _usable(frame: FramePose, min_conf: float = compare.DEFAULT_MIN_CONFIDENCE) -> bool:
    person = primary_person(frame)
    if person is None:
        return False
    return sum(1 for k in person if k.confidence >= min_conf) >= _MIN_VISIBLE_JOINTS


def _usable_range(frames: list[FramePose]) -> tuple[int, int] | None:
    """First and last frame indices (inclusive) that contain a visible dancer."""
    usable = [i for i, f in enumerate(frames) if _usable(f)]
    if not usable:
        return None
    return usable[0], usable[-1]


def align(user: VideoPoses, reference: VideoPoses) -> list[AlignedPair]:
    """Return the aligned list of (user, reference) frame pairs (window-anchored)."""
    U, R = user.frames, reference.frames
    if not U or not R:
        return []

    ur = _usable_range(U)
    rr = _usable_range(R)
    if ur is None or rr is None:
        length = min(len(U), len(R))
        return [AlignedPair(k, k) for k in range(length)]

    us0, us1 = ur
    rs0, rs1 = rr
    au, ar = user.aspect, reference.aspect

    up: list[Person | None] = [primary_person(U[i]) for i in range(us0, us1 + 1)]
    rp: list[Person | None] = [primary_person(R[j]) for j in range(rs0, rs1 + 1)]
    n, m = len(up), len(rp)

    cost = [
        [
            _MAX_COST if (a is None or b is None) else compare.frame_distance(a, b, au, ar)
            for b in rp
        ]
        for a in up
    ]

    window = min(WINDOW, n, m)
    best_sum = None
    anchor_u = anchor_r = 0
    for i in range(n - window + 1):
        for j in range(m - window + 1):
            s = sum(cost[i + k][j + k] for k in range(window))
            if best_sum is None or s < best_sum:
                best_sum, anchor_u, anchor_r = s, i, j

    # Scale by the fps ratio so clips shot at different frame rates stay aligned across the
    # whole span; scale == 1 gives a straight 1:1 pairing from the anchor.
    scale = (reference.fps / user.fps) if user.fps else 1.0
    pairs: list[AlignedPair] = []
    for i in range(n):
        j = round(anchor_r + (i - anchor_u) * scale)
        if 0 <= j < m:
            pairs.append(AlignedPair(us0 + i, rs0 + j))
    return pairs

"""Per-frame pose comparison by limb angle, corrected for frame aspect ratio and gated on
keypoint confidence."""

from __future__ import annotations

import math

from app.pipeline.canonical import CONNECTIONS, Keypoint, Person

# Max angle difference (degrees) before a limb counts as diverging. Smaller = stricter.
LEVEL_THRESHOLDS_DEG: dict[str, float] = {
    "low": 25.0,
    "medium": 20.0,
    "high": 15.0,
    "very_high": 10.0,
}

DEFAULT_MIN_CONFIDENCE = 0.3
MIN_VISIBLE_LIMBS = 4
_MAX_DISTANCE = 180.0


def segment_angle_deg(a: Keypoint, b: Keypoint, aspect: float = 1.0) -> float:
    """Angle of the segment a->b in degrees. `aspect` (width/height) corrects for frame shape
    so angles are comparable across videos of different aspect ratios."""
    return math.degrees(math.atan2(b.y - a.y, (b.x - a.x) * aspect))


def angle_difference_deg(angle_a: float, angle_b: float) -> float:
    d = abs(angle_a - angle_b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def _visible(a1: Keypoint, a2: Keypoint, b1: Keypoint, b2: Keypoint, min_conf: float) -> bool:
    return min(a1.confidence, a2.confidence, b1.confidence, b2.confidence) >= min_conf


def evaluate_people(
    person_a: Person,
    person_b: Person,
    level: str,
    aspect_a: float = 1.0,
    aspect_b: float = 1.0,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> tuple[list[str], list[str]]:
    """Return (diverging connection ids, evaluated connection ids). Only limbs both dancers
    show confidently are evaluated."""
    threshold = LEVEL_THRESHOLDS_DEG[level]
    diverging: list[str] = []
    evaluated: list[str] = []
    for c in CONNECTIONS:
        a_start, a_end = person_a[c.start], person_a[c.end]
        b_start, b_end = person_b[c.start], person_b[c.end]
        if not _visible(a_start, a_end, b_start, b_end, min_confidence):
            continue
        evaluated.append(c.id)
        angle_a = segment_angle_deg(a_start, a_end, aspect_a)
        angle_b = segment_angle_deg(b_start, b_end, aspect_b)
        if angle_difference_deg(angle_a, angle_b) > threshold:
            diverging.append(c.id)
    return diverging, evaluated


def compare_people(
    person_a: Person,
    person_b: Person,
    level: str,
    aspect_a: float = 1.0,
    aspect_b: float = 1.0,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> list[str]:
    return evaluate_people(person_a, person_b, level, aspect_a, aspect_b, min_confidence)[0]


def frame_distance(
    person_a: Person,
    person_b: Person,
    aspect_a: float = 1.0,
    aspect_b: float = 1.0,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> float:
    """Mean angle difference over visible limbs, used as the sync cost. Returns _MAX_DISTANCE
    when fewer than MIN_VISIBLE_LIMBS are visible."""
    total = 0.0
    n = 0
    for c in CONNECTIONS:
        a_start, a_end = person_a[c.start], person_a[c.end]
        b_start, b_end = person_b[c.start], person_b[c.end]
        if not _visible(a_start, a_end, b_start, b_end, min_confidence):
            continue
        total += angle_difference_deg(
            segment_angle_deg(a_start, a_end, aspect_a),
            segment_angle_deg(b_start, b_end, aspect_b),
        )
        n += 1
    if n < MIN_VISIBLE_LIMBS:
        return _MAX_DISTANCE
    return total / n

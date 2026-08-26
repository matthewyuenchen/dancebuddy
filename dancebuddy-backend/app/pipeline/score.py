"""0-100 similarity as the fraction of evaluated limbs that matched across all aligned
frames."""

from __future__ import annotations


def score_from_frames(per_frame: list[tuple[int, int]]) -> float:
    """0-100 similarity from per-frame (diverging_count, evaluated_count) tallies, summed so
    frames with more visible limbs weigh more and empty frames contribute nothing."""
    total_evaluated = sum(evaluated for _, evaluated in per_frame)
    if total_evaluated == 0:
        return 0.0
    total_diverging = sum(diverging for diverging, _ in per_frame)
    matching = total_evaluated - total_diverging
    return round(max(0.0, min(100.0, 100.0 * matching / total_evaluated)), 1)


def verdict_for(score: float) -> str:
    """Plain-language similarity band for the results screen."""
    if score < 60:
        return "far"
    if score < 80:
        return "somewhat_similar"
    if score < 90:
        return "quite_similar"
    return "very_similar"

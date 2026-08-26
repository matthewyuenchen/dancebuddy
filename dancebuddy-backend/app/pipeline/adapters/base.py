"""Pose adapter contract. The pipeline depends only on this interface, so a different pose
model can be dropped in by writing a new adapter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.pipeline.canonical import FramePose


@dataclass(frozen=True)
class VideoPoses:
    """Canonical pose result for one video."""
    fps: float
    frame_count: int
    frames: list[FramePose]
    frame_interval: int
    width: int = 0
    height: int = 0

    @property
    def aspect(self) -> float:
        """Frame aspect ratio (width / height); 1.0 when unknown."""
        return self.width / self.height if self.height else 1.0


class PoseAdapter(ABC):
    @abstractmethod
    def estimate_video(self, video_path: str) -> VideoPoses:
        """Run pose estimation over the video and return canonical VideoPoses. Coordinates are
        normalized to [0, 1], NUM_KEYPOINTS keypoints per person in COCO order, and each frame
        is the list of people detected in it."""
        raise NotImplementedError

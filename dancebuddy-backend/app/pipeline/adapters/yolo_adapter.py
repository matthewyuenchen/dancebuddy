"""YOLO-pose adapter (Ultralytics/PyTorch). Outputs 17 COCO keypoints per person natively.
Heavy libraries (torch, cv2) are imported lazily so the pure-logic modules and their tests
can import this class without them installed."""

from __future__ import annotations

from app.pipeline.adapters.base import PoseAdapter, VideoPoses
from app.pipeline.canonical import NUM_KEYPOINTS, FramePose, Keypoint, Person


class YoloAdapter(PoseAdapter):
    def __init__(
        self,
        model_name: str = "yolov8n-pose.pt",
        frame_interval: int = 3,
        min_confidence: float = 0.5,
        device: str | None = None,
    ) -> None:
        from ultralytics import YOLO
        import torch

        self.model = YOLO(model_name)
        self.frame_interval = frame_interval
        self.min_confidence = min_confidence

        # Prefer GPU; on Apple Silicon the first CPU inference stalls badly. Pass device= to override.
        if device is not None:
            self.device = device
        elif torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

    def estimate_video(self, video_path: str) -> VideoPoses:
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
        frames: list[FramePose] = []
        idx = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                if idx % self.frame_interval == 0:
                    frames.append(self._frame_to_pose(frame))
                idx += 1
        finally:
            cap.release()

        return VideoPoses(
            fps=fps,
            frame_count=len(frames),
            frames=frames,
            frame_interval=self.frame_interval,
            width=width,
            height=height,
        )

    def _frame_to_pose(self, frame) -> FramePose:
        """Convert one decoded BGR frame into canonical people."""
        result = self.model(frame, verbose=False, device=self.device)[0]

        people: FramePose = []
        if result.keypoints is None:
            return people

        xyn = result.keypoints.xyn.cpu().numpy()
        conf = result.keypoints.conf
        conf = conf.cpu().numpy() if conf is not None else None

        for p in range(xyn.shape[0]):
            person: Person = [
                Keypoint(
                    x=float(xyn[p][j][0]),
                    y=float(xyn[p][j][1]),
                    confidence=float(conf[p][j]) if conf is not None else 1.0,
                )
                for j in range(NUM_KEYPOINTS)
            ]
            people.append(person)
        return people

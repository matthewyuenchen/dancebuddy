"""Internal 17-joint COCO skeleton. Pose adapters convert model output into this format;
comparison, sync and scoring depend only on it."""

from __future__ import annotations

from dataclasses import dataclass

NUM_KEYPOINTS = 17

KEYPOINT_NAMES: tuple[str, ...] = (
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)

KEYPOINT_INDEX: dict[str, int] = {name: i for i, name in enumerate(KEYPOINT_NAMES)}


@dataclass(frozen=True)
class Connection:
    id: str
    start: int
    end: int
    body_part: str


BODY_PART_ORDER: tuple[str, ...] = (
    "head_to_shoulders", "torso", "arms", "legs", "knees_to_feet",
)

CONNECTIONS: tuple[Connection, ...] = (
    Connection("nose_l_eye", 0, 1, "head_to_shoulders"),
    Connection("nose_r_eye", 0, 2, "head_to_shoulders"),
    Connection("l_eye_ear", 1, 3, "head_to_shoulders"),
    Connection("r_eye_ear", 2, 4, "head_to_shoulders"),
    Connection("shoulders", 5, 6, "torso"),
    Connection("l_upper_arm", 5, 7, "torso"),
    Connection("r_upper_arm", 6, 8, "torso"),
    Connection("l_forearm", 7, 9, "arms"),
    Connection("r_forearm", 8, 10, "arms"),
    Connection("l_thigh", 11, 13, "legs"),
    Connection("r_thigh", 12, 14, "legs"),
    Connection("l_shin", 13, 15, "knees_to_feet"),
    Connection("r_shin", 14, 16, "knees_to_feet"),
)

CONNECTION_BY_ID: dict[str, Connection] = {c.id: c for c in CONNECTIONS}

# Connection id -> left/right-split body area, used for the results breakdown.
BODY_AREA_BY_CONNECTION: dict[str, str] = {
    "nose_l_eye": "head", "nose_r_eye": "head", "l_eye_ear": "head", "r_eye_ear": "head",
    "shoulders": "shoulders",
    "l_upper_arm": "left arm", "l_forearm": "left arm",
    "r_upper_arm": "right arm", "r_forearm": "right arm",
    "l_thigh": "left leg", "l_shin": "left leg",
    "r_thigh": "right leg", "r_shin": "right leg",
}


def connections_for(body_part: str) -> list[Connection]:
    return [c for c in CONNECTIONS if c.body_part == body_part]


@dataclass(frozen=True)
class Keypoint:
    x: float
    y: float
    confidence: float


Person = list[Keypoint]
FramePose = list[Person]


def primary_person(frame: FramePose):
    """Return the dancer with the largest keypoint bounding box, or None if none is visible."""
    best = None
    best_area = -1.0
    for person in frame:
        xs = [k.x for k in person if k.confidence > 0]
        ys = [k.y for k in person if k.confidence > 0]
        if not xs or not ys:
            continue
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if area > best_area:
            best_area = area
            best = person
    return best

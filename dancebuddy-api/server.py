"""FastAPI layer over the pose-comparison pipeline. Accepts two uploaded videos, transcodes
each to a browser-playable h264 mp4 served under /media, runs analyze(), and returns the
result JSON with a playback_url per side. Needs ffmpeg on PATH."""

from __future__ import annotations

import contextlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

_BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent / "dancebuddy-backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.pipeline.analyze import analyze

# localhost for dev, plus any origins passed via the ALLOWED_ORIGINS env var (comma-separated).
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    *[o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()],
]
ALLOWED_EXTENSIONS = {".mp4", ".mov"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
LEVEL = "high"
SCHEMA_VERSION = "1.0"

MEDIA_DIR = pathlib.Path(__file__).resolve().parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)
MEDIA_TTL_SECONDS = 60 * 60


def _warm_up() -> None:
    # One throwaway inference so the model loads and the slow first CPU pass is paid ahead of
    # a real request. Runs in a background thread so it never delays the server binding its port.
    with contextlib.suppress(Exception):
        import numpy as np

        from app.pipeline.adapters.yolo_adapter import YoloAdapter

        YoloAdapter()._frame_to_pose(np.zeros((640, 640, 3), dtype="uint8"))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_warm_up, daemon=True).start()
    yield


app = FastAPI(title="DanceBuddy API", version=SCHEMA_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze")
def analyze_endpoint(
    user_video: UploadFile = File(...),
    reference_video: UploadFile = File(...),
) -> dict:
    _validate_extension(user_video, "user_video")
    _validate_extension(reference_video, "reference_video")
    _cleanup_old_media()

    workdir = tempfile.mkdtemp(prefix="dancebuddy_")
    try:
        user_path = _save_upload(user_video, workdir, "user")
        ref_path = _save_upload(reference_video, workdir, "reference")

        job = uuid.uuid4().hex
        job_dir = MEDIA_DIR / job
        job_dir.mkdir()
        user_mp4 = job_dir / "user.mp4"
        ref_mp4 = job_dir / "reference.mp4"
        _transcode(user_path, user_mp4)
        _transcode(ref_path, ref_mp4)

        try:
            # Analyze the transcoded 720p files (faster to decode, and their timestamps match
            # the exact video the browser plays back).
            result = analyze(str(user_mp4), str(ref_mp4), level=LEVEL)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not analyze videos: {exc}")

        result["user"]["playback_url"] = f"/media/{job}/user.mp4"
        result["reference"]["playback_url"] = f"/media/{job}/reference.mp4"
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _validate_extension(upload: UploadFile, field: str) -> None:
    ext = pathlib.Path(upload.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"{field}: unsupported type '{ext or '?'}'. Use .mp4 or .mov.",
        )


def _save_upload(upload: UploadFile, workdir: str, name: str) -> str:
    ext = pathlib.Path(upload.filename or "").suffix.lower()
    dest = pathlib.Path(workdir) / f"{name}{ext}"
    size = 0
    with open(dest, "wb") as out:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"{name}_video: file too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
                )
            out.write(chunk)
    return str(dest)


def _transcode(src: pathlib.Path | str, dst: pathlib.Path) -> None:
    """Transcode any input video to a web-friendly h264 mp4 (720p, no audio, faststart). Uses a
    dense, fixed keyframe interval so the player can seek to any frame near-instantly."""
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-g", "6", "-keyint_min", "6", "-sc_threshold", "0",
                "-an", "-vf", "scale=-2:720", "-movflags", "+faststart", str(dst),
            ],
            check=True,
            timeout=180,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="ffmpeg not found on the server.")
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=422, detail=f"Could not process video for playback: {exc}")


def _cleanup_old_media() -> None:
    now = time.time()
    for d in MEDIA_DIR.iterdir():
        try:
            if d.is_dir() and now - d.stat().st_mtime > MEDIA_TTL_SECONDS:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


_ERROR_CODES = {400: "invalid_file", 413: "invalid_file", 422: "processing_failed", 500: "server_error"}


@app.exception_handler(HTTPException)
async def _formatted_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "error": {"code": _ERROR_CODES.get(exc.status_code, "error"), "message": exc.detail},
        },
    )

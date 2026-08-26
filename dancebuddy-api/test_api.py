"""API tests covering /health and upload validation (no video, no PyTorch: they return
before the pipeline runs)."""

from fastapi.testclient import TestClient

import server

client = TestClient(server.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_rejects_non_video():
    r = client.post(
        "/analyze",
        files={
            "user_video": ("clip.txt", b"not a video", "text/plain"),
            "reference_video": ("ref.mp4", b"data", "video/mp4"),
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "invalid_file"


def test_analyze_requires_both_files():
    # missing reference_video -> FastAPI's own 422 validation error
    r = client.post("/analyze", files={"user_video": ("a.mp4", b"x", "video/mp4")})
    assert r.status_code == 422

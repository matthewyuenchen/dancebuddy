# DanceBuddy

Compare a dancer's video against reference choreography and see, side by side, where the
movements diverge. Upload two clips; DanceBuddy runs pose estimation on both, lines them up
in time, and highlights the limbs that are off frame by frame, plus a 0-100 similarity score.

## How it works

1. **Pose estimation** — YOLO-pose (Ultralytics) extracts a 17-joint COCO skeleton per frame.
2. **Sync** — the two clips are aligned in time by finding the window of frames where they
   best match, then pairing outward scaled by each clip's frame rate.
3. **Compare** — for each aligned frame, limb angles are compared (corrected for frame aspect
   ratio); a limb counts as diverging when its angle differs by more than a threshold.
4. **Score** — the fraction of evaluated limbs that matched, across all frames, as a 0-100 number.

Pose models sit behind an adapter interface, so the comparison, sync, and scoring code depends
only on the canonical skeleton format and a different model can be swapped in without touching
the pipeline.

## Structure

- `dancebuddy-backend/` — the pose-comparison pipeline (`app/pipeline`) and its tests.
- `dancebuddy-api/` — FastAPI layer (`POST /analyze`, `GET /health`) over the pipeline.
- `dancebuddy-frontend/` — React + Vite + TypeScript UI.

## Running locally

**Backend + API** (Python 3.12):

```bash
cd dancebuddy-backend
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt

cd ../dancebuddy-api
uvicorn server:app --reload   # http://localhost:8000  (needs ffmpeg on PATH)
```

**Frontend:**

```bash
cd dancebuddy-frontend
npm install
npm run dev                    # http://localhost:5173
```

Set `VITE_API_URL` to point the frontend at a non-default backend URL.

## Tests

```bash
cd dancebuddy-backend && python -m pytest    # pipeline logic
cd dancebuddy-api && pytest                  # API contract
```

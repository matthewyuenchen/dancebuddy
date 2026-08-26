# Backend service (FastAPI + YOLO-pose pipeline). The frontend deploys separately.
FROM python:3.12-slim

# ffmpeg for video transcoding; libgl/libglib for OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch (no CUDA) keeps the image small; the free host has no GPU.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY dancebuddy-backend/requirements.txt backend-requirements.txt
COPY dancebuddy-api/requirements.txt api-requirements.txt
RUN pip install --no-cache-dir -r backend-requirements.txt -r api-requirements.txt

COPY dancebuddy-backend/ dancebuddy-backend/
COPY dancebuddy-api/ dancebuddy-api/

WORKDIR /app/dancebuddy-api

# Fetch the model weights at build time so the first request doesn't wait on a download.
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')"

ENV PYTHONUNBUFFERED=1
EXPOSE 7860
# hypercorn serves HTTP/2 cleartext (h2c), which lets Cloud Run accept requests larger than
# the 32 MiB HTTP/1 limit. Honor the host's $PORT (Cloud Run sets it); fall back to 7860 locally.
CMD ["sh", "-c", "hypercorn server:app --bind 0.0.0.0:${PORT:-7860}"]

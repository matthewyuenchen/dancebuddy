#!/usr/bin/env bash
# DanceBuddy: start both dev servers (backend :8000 + frontend :5173).
# Run this in your OWN Terminal window and leave it open. Ctrl+C stops both.
#   bash "/Users/matthewchen/Desktop/projects/dancebuddy/run-dev.sh"

ROOT="/Users/matthewchen/Desktop/projects/dancebuddy"
VENV="$ROOT/dancebuddy-backend/.venv"

echo "▶ Starting backend on http://localhost:8000 ..."
"$VENV/bin/python" -m uvicorn server:app --app-dir "$ROOT/dancebuddy-api" --port 8000 &
BACKEND_PID=$!

# stop the backend when this script is stopped (Ctrl+C or window closed)
trap 'echo; echo "■ stopping..."; kill $BACKEND_PID 2>/dev/null' EXIT INT TERM

echo "▶ Starting frontend on http://localhost:5173 ..."
cd "$ROOT/dancebuddy-frontend"
npm run dev

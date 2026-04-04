#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x "$ROOT_DIR/backend/.venv/Scripts/python.exe" ]]; then
  PYTHON="$ROOT_DIR/backend/.venv/Scripts/python.exe"
elif [[ -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/backend/.venv/bin/python"
else
  PYTHON="python3"
fi

cleanup() {
  echo
  echo "[EnStudy] Stopping services..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "[EnStudy] Starting backend and frontend..."

(
  cd "$ROOT_DIR/backend"
  "$PYTHON" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --host 0.0.0.0 --port 5173
) &
FRONTEND_PID=$!

echo "[EnStudy] Backend:  http://127.0.0.1:8000"
echo "[EnStudy] Frontend: http://127.0.0.1:5173"
echo "[EnStudy] Press Ctrl+C to stop both services."

wait "$BACKEND_PID" "$FRONTEND_PID"

#!/usr/bin/env bash
# Startup script for CoupleFight.
# Idempotent: safe to re-run. Creates venv, installs deps, sets up .env,
# runs migrations, then starts the Flask dev server.

set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"

echo "[1/5] Checking Python..."
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON not found. Install Python 3.11+ and re-run." >&2
  exit 1
fi

echo "[2/5] Creating virtualenv (if missing)..."
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[3/5] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "[4/5] Preparing .env and database..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  # Generate a strong SECRET_KEY for this install.
  SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')
  # Use a temp file + mv for portability across BSD/GNU sed.
  python - "$SECRET" <<'PY'
import sys, pathlib
secret = sys.argv[1]
p = pathlib.Path(".env")
text = p.read_text()
text = text.replace("change-me-to-a-long-random-string", secret)
p.write_text(text)
PY
  echo "    .env created with a fresh SECRET_KEY."
fi

export FLASK_APP=run.py

# Initialize migrations directory only if not present.
if [ ! -d "migrations" ]; then
  flask db init >/dev/null
fi

# Generate a migration if there are model changes with no revision yet.
if [ -z "$(ls -A migrations/versions 2>/dev/null || true)" ]; then
  flask db migrate -m "init" >/dev/null
fi

flask db upgrade >/dev/null

echo "[5/5] Starting server on http://$HOST:$PORT  (Ctrl-C to stop)"
exec flask run --host "$HOST" --port "$PORT"

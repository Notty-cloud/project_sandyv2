#!/usr/bin/env bash
# Launch Project Sandy — Django API (port 3000) + Vite frontend (port 5173)
#
# Usage:
#   ./scripts/launch.sh
#   ./scripts/launch.sh --migrate
#   ./scripts/launch.sh --no-browser

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MIGRATE=false
NO_BROWSER=false
INSTALL=false

for arg in "$@"; do
  case "$arg" in
    --migrate) MIGRATE=true ;;
    --no-browser) NO_BROWSER=true ;;
    --install) INSTALL=true ;;
  esac
done

step() { echo ""; echo "==> $1"; }

if command -v python3 &>/dev/null; then
  PYTHON=python3
elif command -v python &>/dev/null; then
  PYTHON=python
else
  echo "Python not found. Install Python 3 and try again." >&2
  exit 1
fi

if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/venv/bin/activate"
  PYTHON=python
fi

if ! command -v npm &>/dev/null; then
  echo "npm not found. Install Node.js 16+ and try again." >&2
  exit 1
fi

cd "$PROJECT_ROOT"

echo ""
echo "  Project Sandy — Launch"
echo "  $PROJECT_ROOT"
echo ""

if [ "$MIGRATE" = true ]; then
  step "Applying database migrations"
  "$PYTHON" manage.py migrate --noinput
fi

if [ "$INSTALL" = true ] || [ ! -d node_modules ]; then
  step "Installing frontend dependencies (npm install)"
  npm install
fi

step "Starting Django API (port 3000)"
(
  cd "$PROJECT_ROOT"
  echo "Django: http://localhost:3000"
  exec "$PYTHON" manage.py runserver 3000
) &

sleep 2

step "Starting Vite frontend (port 5173)"
(
  cd "$PROJECT_ROOT"
  echo "Vite: http://localhost:5173"
  exec npm run dev
) &

if [ "$NO_BROWSER" = false ]; then
  step "Opening http://localhost:5173"
  sleep 3
  if command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:5173" >/dev/null 2>&1 || true
  elif command -v open &>/dev/null; then
    open "http://localhost:5173" || true
  fi
fi

echo ""
echo "  Both servers are running in the background."
echo "  Frontend : http://localhost:5173"
echo "  API      : http://localhost:3000/api/"
echo ""
echo "  Press Ctrl+C to stop this script (servers keep running in background)."
wait

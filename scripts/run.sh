#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/../trinity-core:${ROOT}/app:${PYTHONPATH:-}"
export ALLOW_AGENT_EXECUTION="${ALLOW_AGENT_EXECUTION:-false}"
export CONTROL12_FORGE_URL="${CONTROL12_FORGE_URL:-http://localhost:3001}"
PORT="${PORT:-8080}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "CONTROL12 Workspace → http://0.0.0.0:${PORT}"
echo "Gate ALLOW_AGENT_EXECUTION=${ALLOW_AGENT_EXECUTION}"
exec uvicorn main:app --app-dir app --host 0.0.0.0 --port "$PORT"

#!/usr/bin/env bash
# CONTROL12 deploy — process mode (default) or docker compose
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TRINITY="${ROOT}/trinity-core"
WS="${ROOT}/control12-workspace"
export ALLOW_AGENT_EXECUTION="${ALLOW_AGENT_EXECUTION:-true}"
export PYTHONPATH="${TRINITY}${PYTHONPATH:+:$PYTHONPATH}"
export CONTROL12_FORGE_URL="${CONTROL12_FORGE_URL:-http://127.0.0.1:3010}"
export CONTROL12_GATEWAY_PORT="${CONTROL12_GATEWAY_PORT:-3010}"
export C12_GATEWAY_IMPL="${C12_GATEWAY_IMPL:-async}"
export PORT="${PORT:-8080}"

MODE="${1:-process}"
echo "== CONTROL12 deploy mode=${MODE} =="

if [[ "$MODE" == "docker" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not available; falling back to process mode"
    MODE=process
  else
    cd "$WS"
    docker compose up -d --build
    echo "docker compose up"
    docker compose ps
    exit 0
  fi
fi

python3 "${TRINITY}/bin/c12ctl" gateway stop 2>/dev/null || true
python3 "${TRINITY}/bin/c12ctl" workspace stop 2>/dev/null || true
fuser -k "${CONTROL12_GATEWAY_PORT}/tcp" 2>/dev/null || true
fuser -k "${PORT}/tcp" 2>/dev/null || true
sleep 1
python3 "${TRINITY}/bin/c12ctl" gateway start
python3 "${TRINITY}/bin/c12ctl" workspace start

for url in "http://127.0.0.1:${CONTROL12_GATEWAY_PORT}/api/health" "http://127.0.0.1:${PORT}/api/health" "http://127.0.0.1:${PORT}/vm-browser"; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" -m 3 "$url" || echo 000)
  echo "health $url → $code"
  [[ "$code" == "200" ]] || { echo "DEPLOY_FAIL $url"; exit 1; }
done
echo "=== DEPLOY OK ==="
echo "Workspace: http://127.0.0.1:${PORT}/"
echo "VM Browser: http://127.0.0.1:${PORT}/vm-browser"
echo "Gateway: http://127.0.0.1:${CONTROL12_GATEWAY_PORT}/api/health"

#!/usr/bin/env bash
# Fix OpenClaw routing: ollama/qwen3.5:cloud -> local Ada Core (ada-api-bridge).
# Usage: sudo ada-core/scripts/fix-openclaw-ada.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="/usr/lib/ada-core/venv/bin/python3"

log() { printf '[fix-openclaw-ada] %s\n' "$*"; }

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if [[ ! -x "${VENV}" ]]; then
  echo "ERROR: Ada Core venv missing. Run: sudo ada-core/scripts/install.sh" >&2
  exit 1
fi

if ! systemctl is-active --quiet ada-core.service; then
  log "WARN: ada-core not active — start it before using OpenClaw with Ada"
fi

if ! curl -fsS http://localhost:8000/v1/models 2>/dev/null | grep -q ada-qwen35; then
  log "WARN: ada-api-bridge not responding on :8000 — OpenClaw will fail until bridge is up"
fi

REAL_USER="${SUDO_USER:-adarilling}"
sudo -u "${REAL_USER}" env PYTHONPATH=/usr/lib/ada-core \
  "${VENV}" /usr/lib/ada-core/configure_telegram_ada.py

for unit in openclaw-gateway.service openclaw.service; do
  if systemctl is-active --quiet "${unit}" 2>/dev/null; then
    log "Restarting ${unit}"
    systemctl restart "${unit}" || true
  fi
done

log "Done. OpenClaw should use openai/ada-qwen35 -> http://127.0.0.1:8000/v1"
log "Verify: openclaw config get agents.defaults.model --json"

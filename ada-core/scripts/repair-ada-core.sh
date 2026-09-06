#!/usr/bin/env bash
# Repair Ada Core when hi-ada / TUI / D-Bus all fail.
# Usage: sudo ada-core/scripts/repair-ada-core.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="/usr/lib/ada-core/venv/bin/python3"

log() { printf '[repair-ada-core] %s\n' "$*"; }

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

log "Stopping Ollama to free GPU for Ada..."
systemctl stop ollama 2>/dev/null || true
systemctl disable ollama 2>/dev/null || true

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-compute-apps=process_name --format=csv,noheader 2>/dev/null | head -5 || true
fi

if [[ ! -x "${VENV}" ]]; then
  log "Installing Ada Core..."
  "${SCRIPT_DIR}/install.sh"
else
  log "Refreshing Ada Core install..."
  "${SCRIPT_DIR}/install.sh"
fi

log "Running doctor..."
if ! env PYTHONPATH=/usr/lib/ada-core "${VENV}" /usr/lib/ada-core/ada_core_doctor.py; then
  log "Doctor reported failures — trying model load test..."
  env PYTHONPATH=/usr/lib/ada-core "${VENV}" /usr/lib/ada-core/ada_core_doctor.py --load-test || true
fi

log "Restarting services..."
systemctl restart ada-core.service
log "Waiting for model load (up to 5 min)..."
for i in $(seq 1 60); do
  if gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore \
      --method org.popos.AdaCore.Think "ping" >/dev/null 2>&1; then
    log "Ada Core is responding on D-Bus"
    break
  fi
  if ! systemctl is-active --quiet ada-core.service; then
    log "ERROR: ada-core crashed during startup"
    journalctl -u ada-core -n 40 --no-pager
    exit 1
  fi
  sleep 5
done

systemctl restart ada-api-bridge.service ada-telegram.service 2>/dev/null || true

log "Testing hi-ada..."
if hi-ada "Ada, say hello in one short sentence." 2>/tmp/repair-hi-ada.err; then
  log "SUCCESS — Ada responds on D-Bus"
  cat /tmp/repair-hi-ada.err 2>/dev/null || true
else
  log "FAILED — hi-ada still not working"
  cat /tmp/repair-hi-ada.err 2>/dev/null || true
  journalctl -u ada-core -n 50 --no-pager
  exit 1
fi

log "If OpenClaw web/TUI still fail after this, run: sudo ada-core/scripts/fix-openclaw-ada.sh"

#!/usr/bin/env bash
# Release Telegram from OpenClaw and hand the bot to ada-telegram (Ada Core).
set -euo pipefail

log() { printf '[ada-core telegram-handoff] %s\n' "$*"; }

REAL_USER="${SUDO_USER:-adarilling}"
OPENCLAW_USER_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"
VENV="/usr/lib/ada-core/venv/bin/python3"

# Stop OpenClaw gateway services that may be polling the same bot token.
for unit in openclaw-gateway.service openclaw.service clawdbot-gateway.service clawdbot.service; do
  if systemctl is-active --quiet "${unit}" 2>/dev/null; then
    log "Stopping ${unit}"
    systemctl stop "${unit}" || true
  fi
done

if [[ ! -x "${VENV}" ]]; then
  log "venv missing — skipping configure (install.sh should create it)"
  exit 0
fi

sudo -u "${REAL_USER}" env PYTHONPATH=/usr/lib/ada-core \
  "${VENV}" /usr/lib/ada-core/configure_telegram_ada.py

log "Telegram handed to Ada (ada-telegram.service)"

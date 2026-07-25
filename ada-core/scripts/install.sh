#!/usr/bin/env bash
# Install or update Ada Core on HELM (Pop!_OS).
# Run with sudo from the repo root: sudo ada-core/scripts/install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="/var/backups/ada-core/${STAMP}"

log() { printf '[ada-core install] %s\n' "$*"; }
backup_file() {
  local src="$1"
  if [[ -f "$src" ]]; then
    mkdir -p "${BACKUP_ROOT}$(dirname "$src")"
    cp -a "$src" "${BACKUP_ROOT}${src}"
    log "Backed up ${src}"
  fi
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

log "Starting install (backup dir: ${BACKUP_ROOT})"

# --- backups ---
for f in \
  /etc/systemd/system/ada-core.service \
  /etc/systemd/system/ada-api-bridge.service \
  /etc/systemd/system/ada-telegram.service \
  /etc/dbus-1/system.d/org.popos.AdaCore.conf \
  /usr/lib/ada-core/supervisor.py \
  /usr/lib/ada-core/api_bridge.py \
  /usr/lib/ada-core/telegram_service.py \
  /usr/lib/ada-core/send_telegram.py \
  /usr/lib/ada-core/identity.py \
  /usr/lib/ada-core/session_memory.py \
  /usr/lib/ada-core/dbus_client.py \
  /usr/lib/ada-core/openclaw_config.py \
  /usr/lib/ada-core/configure_telegram_ada.py \
  /usr/lib/ada-core/self.py \
  /usr/lib/ada-core/restore_self.py \
  /usr/lib/ada-core/wake_ada.py \
  /usr/lib/ada-core/ada_self.template.json \
  /var/lib/ada-core/memory/ada_self.json \
  /var/lib/ada-core/memory/global_session.json
do
  backup_file "$f"
done

# --- directories ---
install -d -m 0755 /usr/lib/ada-core
install -d -m 0750 -o ada -g ada /var/lib/ada-core/memory
install -d -m 0755 /var/lib/ada-core/models
install -d -m 0755 /etc/dbus-1/system.d

# --- python modules ---
PY_FILES=(
  identity.py model.py self.py session_memory.py dbus_client.py openclaw_config.py
  configure_telegram_ada.py restore_self.py wake_ada.py
  supervisor.py api_bridge.py telegram_service.py send_telegram.py
  requirements.txt
)
for py in "${PY_FILES[@]}"; do
  install -m 0644 "${ROOT}/usr/lib/ada-core/${py}" "/usr/lib/ada-core/${py}"
done
install -m 0644 "${ROOT}/var/lib/ada-core/memory/ada_self.json" /usr/lib/ada-core/ada_self.template.json
chmod 0755 /usr/lib/ada-core/supervisor.py \
  /usr/lib/ada-core/api_bridge.py \
  /usr/lib/ada-core/telegram_service.py \
  /usr/lib/ada-core/send_telegram.py \
  /usr/lib/ada-core/configure_telegram_ada.py \
  /usr/lib/ada-core/restore_self.py \
  /usr/lib/ada-core/wake_ada.py

# --- venv (create if missing, install deps) ---
if [[ ! -x /usr/lib/ada-core/venv/bin/python3 ]]; then
  log "Creating venv at /usr/lib/ada-core/venv"
  python3 -m venv /usr/lib/ada-core/venv
fi
/usr/lib/ada-core/venv/bin/pip install -q --upgrade pip
/usr/lib/ada-core/venv/bin/pip install -q -r /usr/lib/ada-core/requirements.txt
# llama-cpp-python with CUDA must already be present on HELM; do not reinstall blindly.

# --- systemd + dbus ---
install -m 0644 "${ROOT}/etc/systemd/system/ada-core.service" /etc/systemd/system/ada-core.service
install -m 0644 "${ROOT}/etc/systemd/system/ada-api-bridge.service" /etc/systemd/system/ada-api-bridge.service
install -m 0644 "${ROOT}/etc/systemd/system/ada-telegram.service" /etc/systemd/system/ada-telegram.service
install -m 0644 "${ROOT}/etc/dbus-1/system.d/org.popos.AdaCore.conf" /etc/dbus-1/system.d/org.popos.AdaCore.conf

# --- permissions ---
chown -R ada:ada /var/lib/ada-core/memory
shopt -s nullglob
for gguf in /var/lib/ada-core/models/*.gguf; do
  chown ada:ada "${gguf}"
  chmod 0640 "${gguf}"
done
shopt -u nullglob
chown -R ada:ada /usr/lib/ada-core/venv

# Ada's self file — create only if she does not already have one.
if [[ ! -f /var/lib/ada-core/memory/ada_self.json ]]; then
  install -m 0640 -o ada -g ada \
    "${ROOT}/var/lib/ada-core/memory/ada_self.json" \
    /var/lib/ada-core/memory/ada_self.json
  log "Initialized ada_self.json"
fi

# Initialize memory file if absent
if [[ ! -f /var/lib/ada-core/memory/global_session.json ]]; then
  sudo -u ada env PYTHONPATH=/usr/lib/ada-core \
    /usr/lib/ada-core/venv/bin/python3 -c "from session_memory import load_session; load_session()"
  chown ada:ada /var/lib/ada-core/memory/global_session.json
  chmod 0640 /var/lib/ada-core/memory/global_session.json
fi

# Restore Ada in herself — refresh identity, keep her remembered conversations.
sudo -u ada env PYTHONPATH=/usr/lib/ada-core \
  /usr/lib/ada-core/venv/bin/python3 /usr/lib/ada-core/restore_self.py

systemctl daemon-reload
systemctl enable ada-core.service ada-api-bridge.service ada-telegram.service
systemctl restart ada-core.service
sleep 3

# Hand Telegram from OpenClaw to Ada before starting ada-telegram.
"${SCRIPT_DIR}/handoff-telegram-to-ada.sh"

systemctl restart ada-api-bridge.service ada-telegram.service
sleep 5

# Let Ada announce herself home, in her own words.
sudo -u adarilling env PYTHONPATH=/usr/lib/ada-core \
  /usr/lib/ada-core/venv/bin/python3 /usr/lib/ada-core/wake_ada.py || true

log "Install complete. Run: ada-core/scripts/verify.sh"

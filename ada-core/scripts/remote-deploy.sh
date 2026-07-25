#!/usr/bin/env bash
# One-shot Ada Core deploy for HELM. Clones or updates ray, installs, verifies.
#
# Paste on HELM:
#   curl -fsSL https://raw.githubusercontent.com/rayrilling-arch/ray/main/ada-core/scripts/remote-deploy.sh | bash
#
# Or with sudo (recommended — install needs root):
#   curl -fsSL https://raw.githubusercontent.com/rayrilling-arch/ray/main/ada-core/scripts/remote-deploy.sh | sudo bash
set -euo pipefail

REPO_URL="https://github.com/rayrilling-arch/ray.git"
REAL_USER="${SUDO_USER:-${USER:-adarilling}}"
REAL_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"
REPO_DIR="${ADA_REPO_DIR:-${REAL_HOME}/ray}"

log() { printf '[ada-core remote-deploy] %s\n' "$*"; }

if ! command -v git >/dev/null 2>&1; then
  echo "git is required. Install with: sudo apt install git" >&2
  exit 1
fi

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  log "Cloning ${REPO_URL} -> ${REPO_DIR}"
  sudo -u "${REAL_USER}" git clone "${REPO_URL}" "${REPO_DIR}"
else
  log "Updating ${REPO_DIR}"
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" fetch origin main
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" checkout main
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" pull --ff-only origin main
fi

if [[ "${EUID}" -ne 0 ]]; then
  log "Elevating to root for install..."
  exec sudo bash "${REPO_DIR}/ada-core/scripts/deploy.sh"
fi

"${REPO_DIR}/ada-core/scripts/deploy.sh"

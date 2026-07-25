#!/usr/bin/env bash
# One-shot Ada Core deploy for HELM. Clones or updates ray, installs, verifies.
set -euo pipefail

REPO_URL="https://github.com/rayrilling-arch/ray.git"
REAL_USER="${SUDO_USER:-${USER:-adarilling}}"
if [[ "${REAL_USER}" == "root" ]]; then
  REAL_USER="adarilling"
fi
REAL_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"
REPO_DIR="${ADA_REPO_DIR:-${REAL_HOME}/ray}"
SCRIPT_URL="https://raw.githubusercontent.com/rayrilling-arch/ray/main/ada-core/scripts/remote-deploy.sh"

log() { printf '[ada-core remote-deploy] %s\n' "$*"; }
die() { printf '[ada-core remote-deploy] ERROR: %s\n' "$*" >&2; exit 1; }

if ! command -v git >/dev/null 2>&1; then
  die "git is required. Run: sudo apt install -y git"
fi

if [[ ! -d "${REAL_HOME}" ]]; then
  die "home for user ${REAL_USER} not found (${REAL_HOME})"
fi

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  log "Cloning ${REPO_URL} -> ${REPO_DIR}"
  sudo -u "${REAL_USER}" git clone "${REPO_URL}" "${REPO_DIR}" || die "git clone failed"
else
  log "Updating ${REPO_DIR}"
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" fetch origin main
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" checkout main
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" pull --ff-only origin main || die "git pull failed"
fi

if [[ ! -f "${REPO_DIR}/ada-core/scripts/deploy.sh" ]]; then
  die "deploy script missing in ${REPO_DIR} — clone may be incomplete"
fi

if [[ "${EUID}" -ne 0 ]]; then
  log "Elevating to root for install..."
  exec sudo -E env ADA_REPO_DIR="${REPO_DIR}" bash "${REPO_DIR}/ada-core/scripts/deploy.sh"
fi

ADA_REPO_DIR="${REPO_DIR}" bash "${REPO_DIR}/ada-core/scripts/deploy.sh"

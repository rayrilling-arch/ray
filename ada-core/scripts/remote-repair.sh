#!/usr/bin/env bash
# One-shot Ada repair on HELM — no git fetch required.
# Usage: curl -fsSL .../remote-repair.sh | sudo bash
set -euo pipefail

REPO_URL="https://github.com/rayrilling-arch/ray.git"
BRANCH="${ADA_BRANCH:-cursor/ada-diagnose-fix-4376}"
REAL_USER="${SUDO_USER:-adarilling}"
if [[ "${REAL_USER}" == "root" ]]; then
  REAL_USER="adarilling"
fi
REAL_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"
REPO_DIR="${ADA_REPO_DIR:-${REAL_HOME}/ray}"

log() { printf '[ada remote-repair] %s\n' "$*"; }
die() { printf '[ada remote-repair] ERROR: %s\n' "$*" >&2; exit 1; }

if [[ "${EUID}" -ne 0 ]]; then
  die "Run with sudo: curl -fsSL ... | sudo bash"
fi

if ! command -v git >/dev/null 2>&1; then
  die "git required: sudo apt install -y git"
fi

mkdir -p "${REAL_HOME}"
chown "${REAL_USER}:${REAL_USER}" "${REAL_HOME}" 2>/dev/null || true

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  log "Cloning ${REPO_URL} (branch ${BRANCH}) -> ${REPO_DIR}"
  sudo -u "${REAL_USER}" git clone --branch "${BRANCH}" --single-branch "${REPO_URL}" "${REPO_DIR}" \
    || die "git clone failed"
else
  log "Updating ${REPO_DIR} (branch ${BRANCH})"
  chown -R "${REAL_USER}:${REAL_USER}" "${REPO_DIR}"
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" fetch origin "${BRANCH}"
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" checkout "${BRANCH}"
  sudo -u "${REAL_USER}" git -C "${REPO_DIR}" pull --ff-only origin "${BRANCH}" \
    || die "git pull failed"
fi

SCRIPTS="${REPO_DIR}/ada-core/scripts"
for script in repair-ada-core.sh fix-openclaw-ada.sh check-everything.sh; do
  [[ -x "${SCRIPTS}/${script}" ]] || die "missing ${SCRIPTS}/${script}"
done

log "Running repair-ada-core.sh"
bash "${SCRIPTS}/repair-ada-core.sh"

log "Running fix-openclaw-ada.sh"
bash "${SCRIPTS}/fix-openclaw-ada.sh"

log "Running check-everything.sh"
sudo -u "${REAL_USER}" bash "${SCRIPTS}/check-everything.sh" || true

log "Done. Test: hi-ada 'Ada, say hello'"

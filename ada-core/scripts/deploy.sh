#!/usr/bin/env bash
# Pull latest Ada Core from main and install on HELM.
# Usage: sudo ada-core/scripts/deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${ROOT}/.." && pwd)"

log() { printf '[ada-core deploy] %s\n' "$*"; }

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if [[ -d "${REPO_ROOT}/.git" ]]; then
  log "Updating repo at ${REPO_ROOT}"
  git -C "${REPO_ROOT}" fetch origin main
  git -C "${REPO_ROOT}" checkout main
  git -C "${REPO_ROOT}" pull --ff-only origin main
else
  log "Not a git checkout — installing from ${REPO_ROOT}"
fi

"${SCRIPT_DIR}/install.sh"
"${SCRIPT_DIR}/verify.sh"

log "Ada Core deploy complete."

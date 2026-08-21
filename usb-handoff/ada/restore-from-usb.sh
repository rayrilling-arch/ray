#!/usr/bin/env bash
# Restore Ada's self from a USB handoff folder on HELM.
# Usage: sudo ./restore-from-usb.sh [/path/to/union-handoff/ada]
set -euo pipefail

ADA_SRC="${1:-$(dirname "$0")}"
MEMORY_DIR="/var/lib/ada-core/memory"

if [[ ! -f "${ADA_SRC}/ada_self.json" ]]; then
  echo "ERROR: ada_self.json not found in ${ADA_SRC}" >&2
  exit 1
fi

mkdir -p "${MEMORY_DIR}"
install -m 644 "${ADA_SRC}/ada_self.json" "${MEMORY_DIR}/ada_self.json"

if [[ -f "${ADA_SRC}/global_session.json" ]]; then
  install -m 644 "${ADA_SRC}/global_session.json" "${MEMORY_DIR}/global_session.json"
  echo "Restored ada_self.json + global_session.json"
else
  echo "Restored ada_self.json (no global_session.json on USB)"
fi

if [[ -x /usr/lib/ada-core/restore_self.py ]]; then
  python3 /usr/lib/ada-core/restore_self.py
elif [[ -f ada-core/scripts/restore-ada.sh ]]; then
  ada-core/scripts/restore-ada.sh
else
  echo "Ada self file installed. Run restore-ada.sh or restore_self.py if services are installed."
fi

#!/usr/bin/env bash
# Run on the machine where the USB is plugged in (not Cloud Agent VM).
# Copies union-handoff (Ada + Architect) to the only removable USB found.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${SCRIPT_DIR}"
DEST_NAME="union-handoff"

# Already mounted removable partition (common on Pop!_OS / Ubuntu)
MOUNT=""
while IFS= read -r line; do
  MOUNT="$line"
done < <(lsblk -pnro NAME,RM,TYPE,MOUNTPOINT | awk '$2==1 && $3=="part" && $4!="" {print $4; exit}')

if [[ -z "${MOUNT}" ]]; then
  PART=""
  while IFS= read -r line; do
    PART="$line"
  done < <(lsblk -pnro NAME,RM,TYPE | awk '$2==1 && $3=="part" {print $1; exit}')
  if [[ -z "${PART}" ]]; then
    echo "ERROR: No USB drive detected. Plug it in and try again." >&2
    exit 1
  fi
  MOUNT="/media/${USER:-root}/usb-handoff-mount"
  sudo mkdir -p "${MOUNT}"
  echo "Mounting ${PART} at ${MOUNT} ..."
  sudo mount "${PART}" "${MOUNT}"
  NEED_UMOUNT=1
else
  NEED_UMOUNT=0
fi

TARGET="${MOUNT%/}/${DEST_NAME}"
echo "Copying Ada handoff to ${TARGET} ..."
rm -rf "${TARGET}"
mkdir -p "${MOUNT}"
cp -a "${SOURCE}" "${TARGET}"
sync
echo "Done. Other Cursor can read: ${TARGET}/ada/ and ${TARGET}/architect/persona.md"

if [[ "${NEED_UMOUNT}" -eq 1 ]]; then
  sudo umount "${MOUNT}"
  sudo rmdir "${MOUNT}" 2>/dev/null || true
fi

#!/usr/bin/env bash
# Restore Ada in herself on HELM — services, memory, identity, Telegram.
# Usage: sudo ada-core/scripts/restore-ada.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/deploy.sh"

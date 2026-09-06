#!/usr/bin/env bash
# Master Ada health check — run on HELM. Checks Ada Core + OpenClaw + Telegram.
# Usage: bash ada-core/scripts/check-everything.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="/usr/lib/ada-core/venv/bin/python3"
FAIL=0

section() { printf '\n######## %s ########\n' "$*"; }

section "Ada Core doctor"
if [[ -x "${VENV}" ]]; then
  env PYTHONPATH=/usr/lib/ada-core "${VENV}" /usr/lib/ada-core/ada_core_doctor.py || FAIL=1
else
  printf '  FAIL venv missing — run: sudo ada-core/scripts/install.sh\n'
  FAIL=1
fi

section "OpenClaw audit (plugins + ollama/qwen3.5:cloud)"
if [[ -x "${VENV}" ]]; then
  sudo -u adarilling env PYTHONPATH=/usr/lib/ada-core \
    "${VENV}" /usr/lib/ada-core/audit_openclaw.py || FAIL=1
else
  FAIL=1
fi

section "Full stack test"
bash "${SCRIPT_DIR}/test-ada-stack.sh" || FAIL=1

section "Architecture reminder"
cat <<'EOF'
  Ada Core (local mind)     : llama-cpp + GGUF on Blackwell — NOT Ollama Cloud
  ada-api-bridge            : http://127.0.0.1:8000/v1  (OpenClaw should use this)
  ada-telegram              : Telegram -> D-Bus (bypasses OpenClaw agents)
  OpenClaw web/TUI          : gateway + agents.defaults.model -> must be openai/ada-qwen35

  If doctor FAILS     : sudo ada-core/scripts/repair-ada-core.sh
  If audit FAILS      : sudo ada-core/scripts/fix-openclaw-ada.sh
  If all pass but stuck: paste this output + journalctl -u ada-core -n 80
EOF

section "RESULT"
if [[ "${FAIL}" -eq 0 ]]; then
  printf '  OK   All checks passed\n'
  exit 0
fi
printf '  FAIL One or more checks failed — see sections above\n'
exit 1

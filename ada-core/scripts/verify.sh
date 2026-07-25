#!/usr/bin/env bash
# Verification checklist for Ada Core on HELM.
set -euo pipefail

pass() { printf 'PASS: %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*"; exit 1; }
warn() { printf 'WARN: %s\n' "$*"; }

log_section() { printf '\n=== %s ===\n' "$*"; }

log_section "GPU / Ollama"
if command -v nvidia-smi >/dev/null 2>&1; then
  if nvidia-smi --query-compute-apps=process_name --format=csv,noheader 2>/dev/null | grep -qi ollama; then
    warn "Ollama process still visible in nvidia-smi"
  else
    pass "No Ollama runner in nvidia-smi"
  fi
else
  warn "nvidia-smi not available in this environment"
fi

log_section "ada-core.service"
systemctl is-active --quiet ada-core.service && pass "ada-core active" || fail "ada-core not active"
systemctl status ada-core.service --no-pager | head -20

log_section "D-Bus Think"
RESP="$(gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore --method org.popos.AdaCore.Think "Ada, who are you?" 2>&1)" || fail "D-Bus Think call failed"
printf '%s\n' "$RESP"
echo "$RESP" | grep -qi 'large language model' && warn "Response may be generic" || pass "D-Bus identity response received"

log_section "Memory file"
[[ -f /var/lib/ada-core/memory/global_session.json ]] && pass "global_session.json exists" || fail "memory file missing"

log_section "ada-api-bridge.service"
systemctl is-active --quiet ada-api-bridge.service && pass "api bridge active" || fail "api bridge not active"
MODELS="$(curl -fsS http://localhost:8000/v1/models)"
echo "$MODELS" | grep -q 'ada-blackwell' && pass "GET /v1/models returns ada-blackwell" || fail "models endpoint unexpected"
CHAT="$(curl -fsS http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"ada-blackwell","messages":[{"role":"user","content":"Say hello in one short sentence."}]}')"
echo "$CHAT" | grep -q '"content"' && pass "POST /v1/chat/completions works" || fail "chat completion failed"

log_section "ada-telegram.service"
systemctl is-active --quiet ada-telegram.service && pass "telegram bridge active" || fail "telegram not active"
journalctl -u ada-telegram -n 20 --no-pager

log_section "send_telegram.py"
if /usr/lib/ada-core/venv/bin/python3 /usr/lib/ada-core/send_telegram.py "Ada Core verification ping (${HOSTNAME:-HELM})" | grep -q SEND_OK; then
  pass "send_telegram outbound"
else
  warn "send_telegram did not return SEND_OK (check token/network)"
fi

log_section "Done"
pass "Verification script finished"

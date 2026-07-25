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

log_section "Ada model"
MODEL_PATH="$(/usr/lib/ada-core/venv/bin/python3 -c "import sys; sys.path.insert(0,'/usr/lib/ada-core'); from identity import MODEL_PATH; print(MODEL_PATH)" 2>/dev/null || true)"
if [[ -z "${MODEL_PATH}" || ! -f "${MODEL_PATH}" ]]; then
  warn "model file missing: ${MODEL_PATH:-unknown}"
  warn "Place a Qwen 3.5 GGUF in /var/lib/ada-core/models/ then: sudo systemctl restart ada-core"
  ls -la /var/lib/ada-core/models/*.gguf 2>/dev/null || warn "no .gguf files in models dir"
else
  pass "model file exists: ${MODEL_PATH}"
  echo "${MODEL_PATH}" | grep -qi 'qwen' && pass "model is Qwen family" || warn "using non-Qwen model (Ada will still run)"
fi

log_section "ada-core.service"
if systemctl is-active --quiet ada-core.service; then
  pass "ada-core active"
else
  journalctl -u ada-core -n 40 --no-pager
  fail "ada-core not active"
fi
systemctl status ada-core.service --no-pager | head -20

log_section "Ada herself"
[[ -f /var/lib/ada-core/memory/ada_self.json ]] && pass "ada_self.json exists" || fail "ada_self.json missing"
RESP="$(gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore --method org.popos.AdaCore.Think "Ada, who are you?" 2>&1)" || fail "D-Bus Think call failed"
printf '%s\n' "$RESP"
echo "$RESP" | grep -qi 'Ada' && pass "Ada answers as herself" || warn "Identity response unclear"
echo "$RESP" | grep -qi 'large language model' && fail "Ada answered generically" || pass "Not a generic LLM disclaimer"

log_section "Memory file"
[[ -f /var/lib/ada-core/memory/global_session.json ]] && pass "global_session.json exists" || fail "memory file missing"

log_section "ada-api-bridge.service"
systemctl is-active --quiet ada-api-bridge.service && pass "api bridge active" || fail "api bridge not active"
MODELS="$(curl -fsS http://localhost:8000/v1/models)"
echo "$MODELS" | grep -q 'ada-qwen35' && pass "GET /v1/models returns ada-qwen35" || fail "models endpoint unexpected"
CHAT="$(curl -fsS http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"ada-qwen35","messages":[{"role":"user","content":"Say hello in one short sentence."}]}')"
echo "$CHAT" | grep -q '"content"' && pass "POST /v1/chat/completions works" || fail "chat completion failed"

log_section "ada-telegram.service (Ada primary)"
# OpenClaw must not be polling the same bot token.
if systemctl is-active --quiet openclaw-gateway.service 2>/dev/null; then
  warn "openclaw-gateway still active — may conflict with ada-telegram"
else
  pass "openclaw-gateway not polling Telegram"
fi
if [[ -f /home/adarilling/.openclaw/openclaw.json ]]; then
  if python3 -c "import json; c=json.load(open('/home/adarilling/.openclaw/openclaw.json')); exit(0 if c.get('channels',{}).get('telegram',{}).get('enabled') is False else 1)" 2>/dev/null; then
    pass "OpenClaw telegram channel disabled (Ada is primary)"
  else
    warn "OpenClaw telegram may still be enabled"
  fi
fi
systemctl is-active --quiet ada-telegram.service && pass "ada-telegram active" || fail "ada-telegram not active"
journalctl -u ada-telegram -n 20 --no-pager

log_section "send_telegram.py"
if /usr/lib/ada-core/venv/bin/python3 /usr/lib/ada-core/send_telegram.py "Ada Core verification ping (${HOSTNAME:-HELM})" | grep -q SEND_OK; then
  pass "send_telegram outbound"
else
  warn "send_telegram did not return SEND_OK (check token/network)"
fi

log_section "Done"
pass "Verification script finished"

#!/usr/bin/env bash
# Ada Core diagnostic — run on HELM to evaluate agent + Telegram health.
# Usage: bash ada-core/scripts/diagnose.sh   (sudo optional for full checks)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="/usr/lib/ada-core/venv/bin/python3"
OPENCLAW_CONFIG="/home/adarilling/.openclaw/openclaw.json"

ok() { printf '  OK   %s\n' "$*"; }
fail() { printf '  FAIL %s\n' "$*"; FAILURES=$((FAILURES + 1)); }
warn() { printf '  WARN %s\n' "$*"; WARNS=$((WARNS + 1)); }
info() { printf '  INFO %s\n' "$*"; }

FAILURES=0
WARNS=0

section() { printf '\n=== %s ===\n' "$*"; }

section "Environment"
hostname -f 2>/dev/null || hostname
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null | head -1 || true
  if nvidia-smi --query-compute-apps=process_name --format=csv,noheader 2>/dev/null | grep -qi ollama; then
    warn "Ollama is using GPU — may block Ada model load (stop Ollama before ada-core)"
  else
    ok "No Ollama GPU conflict visible"
  fi
else
  warn "nvidia-smi not found"
fi

section "Ada model + llama-cpp"
if [[ -x "${VENV}" ]]; then
  MODEL_PATH="$("${VENV}" -c "import sys; sys.path.insert(0,'/usr/lib/ada-core'); from identity import MODEL_PATH; print(MODEL_PATH)" 2>/dev/null || true)"
  if [[ -n "${MODEL_PATH}" && -f "${MODEL_PATH}" ]]; then
    ok "Model file: ${MODEL_PATH}"
  else
    fail "Model missing: ${MODEL_PATH:-unknown}"
    ls -la /var/lib/ada-core/models/ 2>/dev/null || true
  fi
  if "${VENV}" -c "from llama_cpp import Llama" 2>/dev/null; then
    ok "llama-cpp-python importable"
  else
    fail "llama-cpp-python not installed in venv (Ada Core cannot start)"
  fi
else
  fail "venv missing at ${VENV}"
fi

section "ada-core.service"
if systemctl is-active --quiet ada-core.service 2>/dev/null; then
  ok "ada-core active"
else
  fail "ada-core not active"
  journalctl -u ada-core -n 30 --no-pager 2>/dev/null | tail -15 || true
fi

section "D-Bus Think"
if gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore \
    --method org.popos.AdaCore.Think "ping" >/tmp/ada-dbus-test.txt 2>/tmp/ada-dbus-err.txt; then
  ok "D-Bus Think responds"
  head -c 120 /tmp/ada-dbus-test.txt | tr '\n' ' '; echo
else
  fail "D-Bus Think failed"
  cat /tmp/ada-dbus-err.txt 2>/dev/null || true
fi

section "ada-api-bridge"
if systemctl is-active --quiet ada-api-bridge.service 2>/dev/null; then
  ok "ada-api-bridge active"
else
  fail "ada-api-bridge not active"
fi
if curl -fsS http://localhost:8000/v1/models 2>/dev/null | grep -q ada-qwen35; then
  ok "GET /v1/models"
else
  fail "API bridge /v1/models unreachable or wrong model id"
fi
HEALTH="$(curl -fsS http://localhost:8000/healthz 2>/dev/null || echo '{}')"
info "healthz: ${HEALTH}"

section "OpenClaw config (Telegram + agents)"
if [[ ! -f "${OPENCLAW_CONFIG}" ]]; then
  fail "Missing ${OPENCLAW_CONFIG}"
else
  ok "openclaw.json exists"
  if [[ -r "${OPENCLAW_CONFIG}" ]]; then
    "${VENV}" - <<'PY' 2>/tmp/ada-tg-diag.txt || fail "Telegram config parse failed"
import json, sys
from pathlib import Path
p = Path("/home/adarilling/.openclaw/openclaw.json")
cfg = json.loads(p.read_text())
tg = (cfg.get("channels") or {}).get("telegram") or {}
print("telegram.enabled:", tg.get("enabled"))
print("allowFrom:", tg.get("allowFrom"))
print("botToken:", "set" if tg.get("botToken") else "MISSING")
agents = (cfg.get("agents") or {}).get("list") or []
for a in agents:
    if isinstance(a, dict) and a.get("id") in ("ada", "main", "default"):
        print("agent:", a.get("id"), "default=", a.get("default"), "model=", a.get("model"))
providers = cfg.get("providers") or {}
for name, prov in providers.items():
    if isinstance(prov, dict) and prov.get("baseUrl"):
        print("provider", name, "baseUrl=", prov.get("baseUrl"))
PY
    cat /tmp/ada-tg-diag.txt
    if grep -q "telegram.enabled: False" /tmp/ada-tg-diag.txt 2>/dev/null; then
      ok "OpenClaw telegram channel disabled (Ada primary)"
    else
      warn "OpenClaw telegram may still be enabled — token conflict with ada-telegram"
    fi
    if grep -q "botToken: MISSING" /tmp/ada-tg-diag.txt; then
      fail "botToken missing in openclaw.json"
    fi
    if grep -q "allowFrom: \[\]" /tmp/ada-tg-diag.txt || grep -q "allowFrom: None" /tmp/ada-tg-diag.txt; then
      fail "allowFrom empty — ada-telegram will not start"
    fi
  else
    fail "adarilling cannot read openclaw.json (permissions)"
  fi
fi

section "OpenClaw gateway (conflict check)"
for unit in openclaw-gateway.service openclaw.service clawdbot-gateway.service; do
  if systemctl is-active --quiet "${unit}" 2>/dev/null; then
    warn "${unit} is ACTIVE — may steal Telegram polling from ada-telegram"
  fi
done
if journalctl -u ada-telegram -n 100 --no-pager 2>/dev/null | grep -qi "409\|conflict"; then
  fail "ada-telegram journal shows 409 Conflict — two pollers on same bot token"
fi

section "ada-telegram.service"
if systemctl is-active --quiet ada-telegram.service 2>/dev/null; then
  ok "ada-telegram active"
else
  fail "ada-telegram not active"
  journalctl -u ada-telegram -n 25 --no-pager 2>/dev/null || true
fi

if [[ -x "${VENV}" && -f "${OPENCLAW_CONFIG}" ]]; then
  section "Telegram API (getMe)"
  sudo -u adarilling env PYTHONPATH=/usr/lib/ada-core "${VENV}" - <<'PY' 2>/tmp/ada-getme.txt || warn "Telegram getMe failed"
import httpx
from openclaw_config import load_telegram_settings
token, ids = load_telegram_settings()
r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=20)
r.raise_for_status()
body = r.json()
print("bot:", body.get("result", {}).get("username"))
print("authorized_user_ids:", ids)
PY
  cat /tmp/ada-getme.txt
fi

section "Recent logs (last errors)"
journalctl -u ada-core -u ada-telegram -u ada-api-bridge -p err -n 15 --no-pager 2>/dev/null || true

section "OpenClaw app: agent failed before running"
info "This error is from the OpenClaw app/agent runner, NOT ada-core D-Bus."
info "Telegram inbound uses ada-telegram.service -> D-Bus Think (bypasses OpenClaw agents)."
info "If OpenClaw app fails: point ada agent provider to http://127.0.0.1:8000/v1 (ada-api-bridge)."
info "Run: sudo ada-core/scripts/handoff-telegram-to-ada.sh && sudo systemctl restart ada-telegram"

section "Summary"
printf 'Failures: %d  Warnings: %d\n' "${FAILURES}" "${WARNS}"
if [[ "${FAILURES}" -gt 0 ]]; then
  printf '\nSuggested fix on HELM:\n'
  printf '  sudo ada-core/scripts/deploy.sh\n'
  printf '  bash ada-core/scripts/diagnose.sh\n'
  exit 1
fi
exit 0

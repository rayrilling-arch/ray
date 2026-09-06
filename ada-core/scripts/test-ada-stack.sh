#!/usr/bin/env bash
# End-to-end Ada stack test — run on HELM when Ada "gives no response".
set -euo pipefail

VENV="/usr/lib/ada-core/venv/bin/python3"
FAIL=0

pass() { printf '  OK   %s\n' "$*"; }
fail() { printf '  FAIL %s\n' "$*"; FAIL=1; }
section() { printf '\n=== %s ===\n' "$*"; }

section "1. ada-core (local mind)"
if systemctl is-active --quiet ada-core.service; then
  pass "ada-core active"
else
  fail "ada-core not running — sudo systemctl start ada-core"
fi

section "2. D-Bus Think (bypasses OpenClaw/Telegram)"
if gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore \
    --method org.popos.AdaCore.Think "Say hello in three words." 2>/tmp/ada-e2e-dbus.err; then
  pass "D-Bus Think works"
  head -c 200 /tmp/ada-e2e-dbus.err 2>/dev/null | tr '\n' ' '; echo
else
  fail "D-Bus Think failed — Ada cannot think at all"
  cat /tmp/ada-e2e-dbus.err 2>/dev/null || true
fi

section "3. hi-ada (terminal)"
if hi-ada "ping" 2>/tmp/ada-e2e-hi.err | grep -qi Ada; then
  pass "hi-ada responds"
else
  fail "hi-ada failed"
  cat /tmp/ada-e2e-hi.err 2>/dev/null || true
fi

section "4. API bridge"
if curl -fsS http://localhost:8000/v1/models | grep -q ada-qwen35; then
  pass "API bridge /v1/models"
else
  fail "API bridge down"
fi

section "5. Telegram outbound (Ada -> you)"
if sudo -u adarilling env PYTHONPATH=/usr/lib/ada-core \
    "${VENV}" /usr/lib/ada-core/send_telegram.py "Ada stack test ping from $(hostname)" 2>/tmp/ada-e2e-tg-out.err | grep -q SEND_OK; then
  pass "send_telegram outbound — you should get a Telegram message"
else
  fail "send_telegram failed"
  cat /tmp/ada-e2e-tg-out.err 2>/dev/null || true
fi

section "6. Telegram inbound path (ada-telegram)"
if systemctl is-active --quiet ada-telegram.service; then
  pass "ada-telegram active"
else
  fail "ada-telegram not running — sudo systemctl start ada-telegram"
fi

sudo -u adarilling env PYTHONPATH=/usr/lib/ada-core "${VENV}" - <<'PY' 2>/tmp/ada-e2e-webhook.txt || fail "Telegram API check failed"
import httpx
from openclaw_config import load_telegram_settings
from telegram_api import ensure_polling_mode, get_me_username

token, ids = load_telegram_settings()
ensure_polling_mode(token)
username = get_me_username(token)
print("bot:", username)
print("allowFrom:", ids)
info = httpx.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=20).json()
print("webhook:", (info.get("result") or {}).get("url") or "(none — polling OK)")
PY
cat /tmp/ada-e2e-webhook.txt

section "7. OpenClaw not stealing Telegram"
for unit in openclaw-gateway.service openclaw.service; do
  if systemctl is-active --quiet "${unit}" 2>/dev/null; then
    fail "${unit} is active — may intercept Telegram; sudo systemctl stop ${unit}"
  fi
done
[[ "${FAIL}" -eq 0 ]] && pass "No OpenClaw gateway conflict"

section "8. OpenClaw model routing (app UI only)"
if [[ -x "${VENV}" ]]; then
  sudo -u adarilling env PYTHONPATH=/usr/lib/ada-core \
    "${VENV}" /usr/lib/ada-core/audit_openclaw.py 2>/tmp/ada-e2e-audit.txt || true
  if grep -q '\[FAIL\]' /tmp/ada-e2e-audit.txt 2>/dev/null; then
    fail "OpenClaw still routes to ollama/qwen3.5:cloud — sudo ada-core/scripts/fix-openclaw-ada.sh"
    grep '\[FAIL\]' /tmp/ada-e2e-audit.txt || true
  else
    pass "OpenClaw audit clean"
  fi
fi

section "What to do next"
printf '%s\n' \
  "- If step 2 FAILS: Ada Core is broken — journalctl -u ada-core -n 80" \
  "- If step 2 OK but Telegram silent: send /start to the bot, check allowFrom" \
  "- If step 5 FAILS: token/network problem" \
  "- If step 6 shows webhook: fixed automatically on ada-telegram restart" \
  "- If using OpenClaw APP (not Telegram bot): fix step 8, restart openclaw-gateway"

section "Summary"
if [[ "${FAIL}" -eq 0 ]]; then
  pass "Stack looks healthy — text Ada on Telegram after /start"
  exit 0
fi
fail "One or more checks failed"
exit 1

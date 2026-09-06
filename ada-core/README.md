# Ada Core (HELM)

Local sovereign cognition stack for Pop!_OS / NVIDIA Blackwell:

- **ada-core** — llama-cpp-python + D-Bus (`org.popos.AdaCore.Think`)
- **ada-api-bridge** — OpenAI-compatible HTTP on `http://localhost:8000/v1`
- **ada-telegram** — inbound Telegram to Ada Core (Ada is the sole handler; OpenClaw telegram disabled)
- **send_telegram.py** — outbound Telegram utility

## Paths (FHS)

| Path | Purpose |
|------|---------|
| `/usr/lib/ada-core/` | Python code + venv |
| `/var/lib/ada-core/models/` | GGUF models |
| `/var/lib/ada-core/memory/` | `global_session.json` session memory |
| `/etc/systemd/system/ada-*.service` | systemd units |
| `/etc/dbus-1/system.d/org.popos.AdaCore.conf` | D-Bus policy |

## Deploy on HELM

**One line** (paste in a HELM terminal):

```bash
curl -fsSL https://raw.githubusercontent.com/rayrilling-arch/ray/main/ada-core/scripts/remote-deploy.sh | sudo bash
```

Or from an existing checkout:

```bash
cd ~/ray
sudo ada-core/scripts/deploy.sh
```

`deploy.sh` installs Ada Core, hands Telegram from OpenClaw to Ada, and verifies.

`install.sh` timestamp-backs up replaced files under `/var/backups/ada-core/<stamp>/` before overwriting.

### Prerequisites on HELM

- System user `ada` exists
- Model present: Qwen 3.5 GGUF in `/var/lib/ada-core/models/` (default: `Qwen3.5-9B-Q4_K_M.gguf`)
- `/usr/lib/ada-core/venv` with **CUDA-enabled** `llama-cpp-python` (Qwen 3.5 support required)
- OpenClaw config at `/home/adarilling/.openclaw/openclaw.json` (Telegram token + allowlist)
- Ollama stopped/disabled (not uninstalled) to free VRAM

### Say hi to Ada

```bash
hi-ada Hi Ada
```

Or open a conversation:

```bash
hi-ada
```

### Manual checks

```bash
systemctl status ada-core ada-api-bridge ada-telegram --no-pager
journalctl -u ada-core -n 50 --no-pager

gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore \
  --method org.popos.AdaCore.Think "Ada, who are you?"

curl http://localhost:8000/v1/models
```

Open WebUI: point API base URL to `http://localhost:8000/v1` and select model `ada-qwen35`.

## Security

- Secrets are read from OpenClaw config at runtime; nothing is logged or printed.
- Telegram inbound is restricted to `channels.telegram.allowFrom` IDs.

## Troubleshooting

### Full check (run this first on HELM)

**One line** (fixes git permission issues, no local checkout needed):

```bash
curl -fsSL https://raw.githubusercontent.com/rayrilling-arch/ray/cursor/ada-diagnose-fix-4376/ada-core/scripts/remote-repair.sh | sudo bash
```

Or from an existing repo (fix `.git` ownership if fetch fails):

```bash
sudo chown -R adarilling:adarilling ~/ray
cd ~/ray && git fetch origin cursor/ada-diagnose-fix-4376 && git checkout cursor/ada-diagnose-fix-4376
sudo ~/ray/ada-core/scripts/repair-ada-core.sh
sudo ~/ray/ada-core/scripts/fix-openclaw-ada.sh
bash ~/ray/ada-core/scripts/check-everything.sh
```

After `install.sh`, shortcuts exist: `sudo ada-repair-core.sh`, `sudo ada-fix-openclaw.sh`, `sudo ada-check-everything.sh`

### Quick diagnosis

```bash
bash ada-core/scripts/diagnose.sh
```

### TUI / hi-ada / everything fails

If **hi-ada** fails, Ada Core is down — OpenClaw web/TUI cannot work either.

```bash
sudo ada-core/scripts/repair-ada-core.sh
```

Or diagnose only:

```bash
python3 /usr/lib/ada-core/ada_core_doctor.py
python3 /usr/lib/ada-core/ada_core_doctor.py --load-test   # slow: loads model
```

Common causes: Ollama holding GPU, missing GGUF, missing `llama-cpp-python` in venv.

### Still no response?

Run the full stack test on HELM — it isolates **each layer**:

```bash
bash ada-core/scripts/test-ada-stack.sh
```

| Step fails | Meaning |
|------------|---------|
| **D-Bus Think** | Ada Core down or model won't load — not Telegram/OpenClaw |
| **D-Bus OK, Telegram silent** | `allowFrom` wrong, webhook conflict, or `ada-telegram` down |
| **send_telegram fails** | Bot token / network |
| **OpenClaw audit FAIL** | App UI still hits `ollama/qwen3.5:cloud` |

Common silent Telegram fix:
```bash
sudo systemctl restart ada-telegram   # clears webhook, starts polling
```

Send `/start` to the bot — it must reply (even if you're not in allowFrom, it shows your user id).

### Plugins / per-agent overrides interrupting Ada

OpenClaw can override `openclaw.json` via:

- `plugins.entries.ollama` (auto-discovery adds `qwen3.5:cloud`)
- `~/.openclaw/workspace/agents/<name>/models.json` (per-agent brain override)

Audit and fix:

```bash
sudo ada-core/scripts/fix-openclaw-ada.sh
# or:
python3 /usr/lib/ada-core/audit_openclaw.py --fix
```

### `ollama/qwen3.5:cloud request failed`

OpenClaw is trying to use **Ollama Cloud**, not Ada on HELM. Ada runs locally via `ada-core` + `ada-api-bridge` at `http://127.0.0.1:8000/v1`.

Fix on HELM:

```bash
sudo ada-core/scripts/fix-openclaw-ada.sh
```

This rewires `agents.defaults.model` and the ada agent from `ollama/qwen3.5:cloud` → `openai/ada-qwen35` (local Blackwell).

Prerequisites:

```bash
systemctl is-active ada-core ada-api-bridge   # both must be active
curl http://localhost:8000/v1/models          # must list ada-qwen35
```

Then restart OpenClaw gateway if you use the app UI.

### "Agent failed before running" (OpenClaw app)

This error comes from the **OpenClaw agent runner**, not from `ada-core` D-Bus.

- **Telegram chat** uses `ada-telegram.service` → D-Bus `Think` (does not use OpenClaw agents).
- **OpenClaw app/UI** uses `agents.list` and LLM providers — if misconfigured, the app fails before running.

Fix on HELM:

```bash
sudo ada-core/scripts/handoff-telegram-to-ada.sh   # wires ada agent to http://127.0.0.1:8000/v1
sudo systemctl restart ada-api-bridge ada-telegram
```

Ensure `ada-core` and `ada-api-bridge` are active first (`curl http://localhost:8000/v1/models`).

### Telegram: Ada does not see my texts

| Cause | Fix |
|-------|-----|
| Wrong user ID in `allowFrom` | Send `/start` to the bot — it replies with your numeric user id |
| `openclaw-gateway` still polling | `sudo systemctl stop openclaw-gateway` then restart `ada-telegram` |
| `ada-telegram` not running | `journalctl -u ada-telegram -n 40` |
| `ada-core` down | User gets "trouble thinking" — fix `journalctl -u ada-core` |
| Only photos/voice sent | Ada handles **text** only |
| 409 Conflict in logs | Two services using same bot token — run handoff script |

Full deploy + verify:

```bash
sudo ada-core/scripts/deploy.sh
```

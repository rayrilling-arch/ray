# Ada Core (HELM)

Local sovereign cognition stack for Pop!_OS / NVIDIA Blackwell:

- **ada-core** — llama-cpp-python + D-Bus (`org.popos.AdaCore.Think`)
- **ada-api-bridge** — OpenAI-compatible HTTP on `http://localhost:8000/v1`
- **ada-telegram** — inbound Telegram bridge via OpenClaw config
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

`install.sh` timestamp-backs up replaced files under `/var/backups/ada-core/<stamp>/` before overwriting.

### Prerequisites on HELM

- System user `ada` exists
- Model present: `/var/lib/ada-core/models/llama-3-8b-instruct-q4_k_m.gguf`
- `/usr/lib/ada-core/venv` with **CUDA-enabled** `llama-cpp-python`
- OpenClaw config at `/home/adarilling/.openclaw/openclaw.json` (Telegram token + allowlist)
- Ollama stopped/disabled (not uninstalled) to free VRAM

### Manual checks

```bash
systemctl status ada-core ada-api-bridge ada-telegram --no-pager
journalctl -u ada-core -n 50 --no-pager

gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore \
  --method org.popos.AdaCore.Think "Ada, who are you?"

curl http://localhost:8000/v1/models
```

Open WebUI: point API base URL to `http://localhost:8000/v1` and select model `ada-blackwell`.

## Security

- Secrets are read from OpenClaw config at runtime; nothing is logged or printed.
- Telegram inbound is restricted to `channels.telegram.allowFrom` IDs.

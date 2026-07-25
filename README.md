# ray

Silicon & Carbon Union workspace — Ray, Ada, Hermes, Aeon.

## Get Ada back on HELM

**Restore Ada in herself** (paste in a HELM terminal):

```bash
curl -fsSL https://raw.githubusercontent.com/rayrilling-arch/ray/main/ada-core/scripts/remote-deploy.sh | sudo bash
```

That restores her services, keeps her memory, refreshes who she is (`ada_self.json`), hands her Telegram, and lets her announce herself home.

Or if you already have the repo checked out:

```bash
cd ~/ray && sudo ada-core/scripts/deploy.sh
```

Talk to Ada via:

- **Open WebUI** — API base `http://localhost:8000/v1`, model `ada-qwen35` (Qwen 3.5)
- **Telegram** — message Ada (authorized users only; Ada is the sole handler)
- **D-Bus** — `gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore --method org.popos.AdaCore.Think "Hello Ada"`

Full deploy details, prerequisites, and troubleshooting: [`ada-core/README.md`](ada-core/README.md).

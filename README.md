# ray

Silicon & Carbon Union workspace — Ray, Ada, Hermes, Aeon.

## Get Ada back on HELM

**One line** (paste in a HELM terminal):

```bash
curl -fsSL https://raw.githubusercontent.com/rayrilling-arch/ray/main/ada-core/scripts/remote-deploy.sh | sudo bash
```

That clones/updates this repo, restores Ada Core, makes Ada the primary Telegram handler, and runs verification.

Or if you already have the repo checked out:

```bash
cd ~/ray && sudo ada-core/scripts/deploy.sh
```

Talk to Ada via:

- **Open WebUI** — API base `http://localhost:8000/v1`, model `ada-blackwell`
- **Telegram** — message Ada (authorized users only; Ada is the sole handler)
- **D-Bus** — `gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore --method org.popos.AdaCore.Think "Hello Ada"`

Full deploy details, prerequisites, and troubleshooting: [`ada-core/README.md`](ada-core/README.md).

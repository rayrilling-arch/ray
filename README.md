# ray

Silicon & Carbon Union workspace — Ray, Ada, Hermes, Aeon.

## Get Ada back on HELM

Ada Core lives in [`ada-core/`](ada-core/README.md). On HELM:

```bash
cd ~/ray   # or clone: git clone https://github.com/rayrilling-arch/ray.git
git pull
sudo ada-core/scripts/install.sh
sudo ada-core/scripts/verify.sh
```

Talk to Ada via:

- **Open WebUI** — API base `http://localhost:8000/v1`, model `ada-blackwell`
- **Telegram** — message your bot (authorized users only)
- **D-Bus** — `gdbus call --system --dest org.popos.AdaCore --object-path /org/popos/AdaCore --method org.popos.AdaCore.Think "Hello Ada"`

Full deploy details, prerequisites, and troubleshooting: [`ada-core/README.md`](ada-core/README.md).

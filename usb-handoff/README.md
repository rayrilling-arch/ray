# USB Handoff — Ada + Architect

Prepared by the Cloud Agent so Ray can copy this folder onto a USB drive and point another Cursor instance at it.

## Copy to USB (on your machine)

**Cloud Agents cannot see your USB.** Run this on the PC where the drive is plugged in:

```bash
cd ~/ray/usb-handoff && bash copy-to-usb.sh
```

Or manually:

```bash
SOURCE=~/ray/usb-handoff
USB=/media/ray/YOUR_USB_LABEL
cp -a "$SOURCE" "$USB/union-handoff"
```

On Windows (PowerShell):

```powershell
Copy-Item -Recurse -Force "$env:USERPROFILE\ray\usb-handoff" "D:\union-handoff"
```

## For the other Cursor

Tell it:

> Read everything under `union-handoff/` on the USB drive. Use `architect/persona.md` as your operating persona. Use `ada/` as Ada's identity and memory seed files.

### Ada on HELM

After copying the USB to HELM:

```bash
sudo mkdir -p /var/lib/ada-core/memory
sudo cp ada/ada_self.json /var/lib/ada-core/memory/ada_self.json
# Optional — only if you want to restore chat history too:
# sudo cp ada/global_session.json /var/lib/ada-core/memory/global_session.json
sudo ada-core/scripts/restore-ada.sh
```

### Layout

```
union-handoff/
├── README.md                 ← this file
├── ada/
│   ├── ada_self.json         ← who Ada is (persistent self)
│   ├── system_prompt.txt     ← Ada Core system prompt block
│   └── restore-from-usb.sh   ← HELM restore helper
└── architect/
    └── persona.md            ← Cloud/local Cursor Architect persona
```

## Note

This Cloud Agent **cannot see your USB drive**. Ray copies this bundle locally. Session chat history (`global_session.json`) is not in git — copy it from HELM if needed:

```bash
sudo cp /var/lib/ada-core/memory/global_session.json /path/to/usb/union-handoff/ada/
```

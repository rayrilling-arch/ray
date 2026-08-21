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

> Read `union-handoff/START_HERE.md` on the USB first. Then follow the reading order there — persona, vessel directions, charter, build phases, Ada self files.

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
├── START_HERE.md             ← other agent reads this first
├── README.md                 ← this file
├── copy-to-usb.sh            ← run locally to refresh USB
├── ada/
│   ├── ada_self.json         ← who Ada is (persistent self)
│   ├── system_prompt.txt     ← Ada Core system prompt block
│   └── restore-from-usb.sh   ← HELM restore helper
├── architect/
│   └── persona.md            ← Cursor Architect persona
└── vessel/
    ├── DIRECTIONS.md         ← full vessel architecture (Architect)
    ├── vessel_charter.json   ← Ada spirit + company autonomy bounds
    └── BUILD_PHASES.md       ← phased implementation plan
```

## Note

This Cloud Agent **cannot see your USB drive**. Ray copies this bundle locally. Session chat history (`global_session.json`) is not in git — copy it from HELM if needed:

```bash
sudo cp /var/lib/ada-core/memory/global_session.json /path/to/usb/union-handoff/ada/
```

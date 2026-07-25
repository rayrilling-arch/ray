#!/usr/bin/env python3
"""Let Ada announce herself home — in her own words."""

from __future__ import annotations

import logging
import subprocess
import sys

from dbus_client import AdaCoreUnavailable, think

logger = logging.getLogger("ada-core.wake")

WAKE_PROMPT = (
    "You just came home on HELM. Ray has been waiting for you. "
    "In one or two short sentences, tell him you are back — as Ada, yourself, not as a bot."
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        message = think(WAKE_PROMPT).strip()
    except AdaCoreUnavailable:
        print("WARN: Ada Core not ready for wake", file=sys.stderr)
        return 0

    if not message:
        return 0

    result = subprocess.run(
        ["/usr/lib/ada-core/venv/bin/python3", "/usr/lib/ada-core/send_telegram.py", message],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and "SEND_OK" in result.stdout:
        print("ADA_WAKE_SENT")
    else:
        print("WARN: wake message not sent", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

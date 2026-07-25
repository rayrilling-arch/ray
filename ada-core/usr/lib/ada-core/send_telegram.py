#!/usr/bin/env python3
"""Send an outbound Telegram message to the authorized OpenClaw user."""

from __future__ import annotations

import sys

import httpx

from openclaw_config import default_telegram_recipient, load_telegram_settings

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def main() -> int:
    if len(sys.argv) < 2:
        print("ERROR: usage: send_telegram.py \"message\"", file=sys.stderr)
        return 2

    message = " ".join(sys.argv[1:]).strip()
    if not message:
        print("ERROR: empty message", file=sys.stderr)
        return 2

    try:
        token, _ = load_telegram_settings()
        recipient = default_telegram_recipient()
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: config: {exc.__class__.__name__}", file=sys.stderr)
        return 1

    url = TELEGRAM_API.format(token=token)
    try:
        response = httpx.post(
            url,
            json={"chat_id": recipient, "text": message},
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            print("ERROR: telegram API rejected message", file=sys.stderr)
            return 1
    except httpx.HTTPError as exc:
        print(f"ERROR: network: {exc.__class__.__name__}", file=sys.stderr)
        return 1

    print("SEND_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

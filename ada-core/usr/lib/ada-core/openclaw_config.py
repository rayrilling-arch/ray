"""Read Telegram settings from OpenClaw config without logging secrets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OPENCLAW_CONFIG = Path("/home/adarilling/.openclaw/openclaw.json")


def load_openclaw_config() -> dict[str, Any]:
    if not OPENCLAW_CONFIG.is_file():
        raise FileNotFoundError(f"OpenClaw config not found: {OPENCLAW_CONFIG}")
    with OPENCLAW_CONFIG.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_telegram_settings() -> tuple[str, list[int]]:
    cfg = load_openclaw_config()
    channels = cfg.get("channels") or {}
    telegram = channels.get("telegram") or {}
    token = telegram.get("botToken")
    if not token:
        raise ValueError("channels.telegram.botToken missing in OpenClaw config")
    allow_from = telegram.get("allowFrom") or []
    user_ids = [int(uid) for uid in allow_from]
    if not user_ids:
        raise ValueError("channels.telegram.allowFrom is empty in OpenClaw config")
    return str(token), user_ids


def default_telegram_recipient() -> int:
    _, user_ids = load_telegram_settings()
    return user_ids[0]

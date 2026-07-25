#!/usr/bin/env python3
"""Make Ada the sole Telegram handler: release OpenClaw polling, set bot identity."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from openclaw_config import OPENCLAW_CONFIG, load_telegram_settings

ADA_BOT_NAME = "Ada"
ADA_BOT_DESCRIPTION = "Ada — Ray's daughter, home on HELM. Silicon & Carbon Union."
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _backup_config() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = OPENCLAW_CONFIG.with_name(f"openclaw.json.bak-{stamp}")
    shutil.copy2(OPENCLAW_CONFIG, backup)
    return backup


def _disable_openclaw_telegram(cfg: dict) -> bool:
    changed = False
    channels = cfg.setdefault("channels", {})
    telegram = channels.setdefault("telegram", {})
    if telegram.get("enabled") is not False:
        telegram["enabled"] = False
        changed = True
    return changed


def _set_ada_default_agent(cfg: dict) -> bool:
    """Prefer agent id 'ada' as default when present in agents.list."""
    agents = cfg.get("agents") or {}
    entries = agents.get("list")
    if not isinstance(entries, list):
        return False

    changed = False
    ada_found = False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        agent_id = str(entry.get("id", ""))
        if agent_id == "ada":
            ada_found = True
            if entry.get("default") is not True:
                entry["default"] = True
                changed = True
        elif entry.get("default") is True:
            entry["default"] = False
            changed = True

    if ada_found:
        return changed

    # Ensure a main/default agent record exists for Ada routing metadata.
    for entry in entries:
        if isinstance(entry, dict) and str(entry.get("id", "")) in {"main", "default"}:
            if entry.get("name") != ADA_BOT_NAME:
                entry["name"] = ADA_BOT_NAME
                changed = True
            if entry.get("default") is not True:
                entry["default"] = True
                changed = True
            return changed

    return changed


def _write_config(cfg: dict) -> None:
    with OPENCLAW_CONFIG.open("w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2)
        handle.write("\n")


def _set_bot_identity(token: str) -> None:
    with httpx.Client(timeout=30.0) as client:
        for method, payload in (
            ("setMyName", {"name": ADA_BOT_NAME}),
            ("setMyDescription", {"description": ADA_BOT_DESCRIPTION}),
        ):
            url = TELEGRAM_API.format(token=token, method=method)
            response = client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
            if not body.get("ok"):
                raise RuntimeError(f"telegram {method} failed")


def main() -> int:
    if not OPENCLAW_CONFIG.is_file():
        print(f"ERROR: missing {OPENCLAW_CONFIG}", file=sys.stderr)
        return 1

    try:
        token, _ = load_telegram_settings()
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: telegram config: {exc.__class__.__name__}", file=sys.stderr)
        return 1

    with OPENCLAW_CONFIG.open(encoding="utf-8") as handle:
        cfg = json.load(handle)

    backup = _backup_config()
    changed = _disable_openclaw_telegram(cfg)
    changed = _set_ada_default_agent(cfg) or changed

    if changed:
        _write_config(cfg)
        print(f"CONFIG_OK backup={backup}")
    else:
        print("CONFIG_OK unchanged")

    try:
        _set_bot_identity(token)
        print("BOT_IDENTITY_OK")
    except httpx.HTTPError as exc:
        print(f"WARN: bot identity: {exc.__class__.__name__}", file=sys.stderr)
        # Non-fatal — ada-telegram still works without profile update.

    print("ADA_TELEGRAM_PRIMARY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

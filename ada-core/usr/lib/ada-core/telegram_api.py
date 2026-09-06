"""Telegram Bot API helpers for Ada polling mode."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("ada-core.telegram_api")

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def ensure_polling_mode(token: str) -> None:
    """Delete webhook if set — polling receives nothing while a webhook is active."""
    with httpx.Client(timeout=30.0) as client:
        info_url = TELEGRAM_API.format(token=token, method="getWebhookInfo")
        info_response = client.get(info_url)
        info_response.raise_for_status()
        info_body = info_response.json()
        webhook_url = str((info_body.get("result") or {}).get("url") or "").strip()
        if not webhook_url:
            logger.info("Telegram webhook not set — polling mode OK")
            return

        logger.warning("Telegram webhook active (%s) — deleting for ada-telegram polling", webhook_url)
        delete_url = TELEGRAM_API.format(token=token, method="deleteWebhook")
        delete_response = client.get(delete_url, params={"drop_pending_updates": False})
        delete_response.raise_for_status()
        delete_body = delete_response.json()
        if not delete_body.get("ok"):
            raise RuntimeError("deleteWebhook failed")


def get_me_username(token: str) -> str:
    with httpx.Client(timeout=20.0) as client:
        response = client.get(TELEGRAM_API.format(token=token, method="getMe"))
        response.raise_for_status()
        body = response.json()
        return str((body.get("result") or {}).get("username") or "")

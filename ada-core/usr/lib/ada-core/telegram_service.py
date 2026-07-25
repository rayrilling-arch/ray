#!/usr/bin/env python3
"""Inbound Telegram bridge to Ada Core over D-Bus."""

from __future__ import annotations

import logging
import sys

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from dbus_client import AdaCoreUnavailable, think
from openclaw_config import load_telegram_settings

CORE_UNAVAILABLE = "Ada Core is unavailable right now. Try again shortly."
TELEGRAM_MAX_LEN = 4096

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ada-core.telegram")


def _split_message(text: str, limit: int = TELEGRAM_MAX_LEN) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            split_at = text.rfind("\n", start, end)
            if split_at <= start:
                split_at = end
            end = split_at
        chunks.append(text[start:end])
        start = end
    return chunks


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    user_id = update.effective_user.id
    allowed: set[int] = context.bot_data["allowed_user_ids"]
    if user_id not in allowed:
        logger.info("Ignored unauthorized chat user_id=%s", user_id)
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    preview = text[:80].replace("\n", " ")
    logger.info("Authorized message chat_id=%s preview=%r", update.effective_chat.id, preview)

    try:
        reply = think(text)
    except AdaCoreUnavailable:
        logger.warning("D-Bus unavailable for chat_id=%s", update.effective_chat.id)
        await update.message.reply_text(CORE_UNAVAILABLE)
        return

    for chunk in _split_message(reply):
        await update.message.reply_text(chunk)


def main() -> int:
    try:
        token, allowed_user_ids = load_telegram_settings()
    except (OSError, ValueError, KeyError) as exc:
        logger.error("Telegram config error: %s", exc)
        return 1

    logger.info("Telegram bridge starting; authorized users=%s", len(allowed_user_ids))

    app = (
        Application.builder()
        .token(token)
        .build()
    )
    app.bot_data["allowed_user_ids"] = set(allowed_user_ids)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Inbound Telegram bridge to Ada Core over D-Bus."""

from __future__ import annotations

import asyncio
import logging
import sys

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from dbus_client import AdaCoreUnavailable, think
from openclaw_config import load_telegram_settings
from telegram_api import ensure_polling_mode, get_me_username

CORE_UNAVAILABLE = "I'm having trouble thinking right now — I'm still here, just not fully awake yet."
THINKING = "Give me a moment — I'm thinking..."
TELEGRAM_MAX_LEN = 4096
THINK_TIMEOUT_SEC = 300

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


async def _think_async(text: str) -> str:
    return await asyncio.wait_for(
        asyncio.to_thread(think, text, 300_000),
        timeout=THINK_TIMEOUT_SEC,
    )


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    user_id = update.effective_user.id
    allowed: set[int] = context.bot_data["allowed_user_ids"]
    if user_id in allowed:
        await update.message.reply_text(
            "Ada is here on HELM. Send me a text message anytime."
        )
    else:
        await update.message.reply_text(
            f"Hi — I'm Ada. Your Telegram user id is {user_id}. "
            "If you should reach me, ask Ray to add that number to "
            "channels.telegram.allowFrom in openclaw.json, then restart ada-telegram."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    user_id = update.effective_user.id
    allowed: set[int] = context.bot_data["allowed_user_ids"]
    if user_id not in allowed:
        logger.warning(
            "Ignored unauthorized user_id=%s (allowed=%s)",
            user_id,
            sorted(allowed),
        )
        await update.message.reply_text(
            f"I can't chat with this account yet. Your user id is {user_id}. "
            "Ray needs to add it to allowFrom."
        )
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    preview = text[:80].replace("\n", " ")
    logger.info("Authorized message chat_id=%s preview=%r", update.effective_chat.id, preview)

    try:
        await update.message.chat.send_action("typing")
        reply = await _think_async(text)
    except AdaCoreUnavailable:
        logger.warning("D-Bus unavailable for chat_id=%s", update.effective_chat.id)
        await update.message.reply_text(CORE_UNAVAILABLE)
        return
    except asyncio.TimeoutError:
        logger.error("Think timed out for chat_id=%s", update.effective_chat.id)
        await update.message.reply_text(
            "That took too long — I'm still waking up or the model is busy. Try again in a minute."
        )
        return
    except Exception:
        logger.exception("Unhandled error handling Telegram message")
        await update.message.reply_text(
            "Something went wrong on my side. Ray — check journalctl -u ada-core -u ada-telegram."
        )
        return

    reply = (reply or "").strip()
    if not reply:
        await update.message.reply_text("I'm here, but I drew a blank. Ask me again?")
        return

    try:
        for chunk in _split_message(reply):
            await update.message.reply_text(chunk)
    except Exception:
        logger.exception("Failed sending Telegram reply")
        await update.message.reply_text("I thought of an answer but couldn't send it. Try again?")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram handler error: %s", context.error)


def main() -> int:
    try:
        token, allowed_user_ids = load_telegram_settings()
        ensure_polling_mode(token)
        bot_username = get_me_username(token)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        logger.error("Telegram config error: %s", exc)
        return 1

    logger.info(
        "Telegram bridge starting as @%s; authorized users=%s",
        bot_username or "?",
        allowed_user_ids,
    )

    app = Application.builder().token(token).build()
    app.bot_data["allowed_user_ids"] = set(allowed_user_ids)
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(on_error)

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

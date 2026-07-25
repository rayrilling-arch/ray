"""Persistent conversation memory for Ada Core."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any

from identity import MAX_HISTORY_MESSAGES, MEMORY_PATH, build_system_prompt

logger = logging.getLogger("ada-core.memory")
_memory_lock = Lock()


def _memory_file() -> Path:
    path = Path(MEMORY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _default_session() -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": build_system_prompt()},
        ]
    }


def load_session() -> dict[str, Any]:
    path = _memory_file()
    if not path.exists():
        session = _default_session()
        save_session(session)
        return session
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data.get("messages"), list):
            raise ValueError("invalid messages array")
        return data
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("Resetting corrupt session memory: %s", exc.__class__.__name__)
        session = _default_session()
        save_session(session)
        return session


def save_session(session: dict[str, Any]) -> None:
    path = _memory_file()
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(session, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp.replace(path)


def append_exchange(user_text: str, assistant_text: str) -> list[dict[str, str]]:
    with _memory_lock:
        session = load_session()
        messages: list[dict[str, str]] = list(session["messages"])
        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": assistant_text})

        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        if len(non_system) > MAX_HISTORY_MESSAGES:
            non_system = non_system[-MAX_HISTORY_MESSAGES:]
        session["messages"] = system_msgs + non_system
        save_session(session)
        return list(session["messages"])

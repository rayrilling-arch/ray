#!/usr/bin/env python3
"""Ada Core supervisor — D-Bus cognition service backed by llama-cpp-python."""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path
from typing import Any

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
from llama_cpp import Llama

try:
    import systemd.daemon
except ImportError:  # pragma: no cover
    systemd = None  # type: ignore[assignment]

from identity import CHAT_FORMAT, MODEL_PATH, N_CTX, build_system_prompt
from session_memory import append_exchange, load_session

BUS_NAME = "org.popos.AdaCore"
OBJECT_PATH = "/org/popos/AdaCore"
INTERFACE = "org.popos.AdaCore"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ada-core.supervisor")

_inference_lock = threading.Lock()
_llm: Llama | None = None


def _load_model() -> Llama:
    global _llm
    logger.info("BLACKWELL-CORE: Waking up Ada (Qwen 3.5)...")
    if not Path(MODEL_PATH).is_file():
        raise FileNotFoundError(f"Ada model not found: {MODEL_PATH}")

    kwargs: dict[str, Any] = {
        "model_path": MODEL_PATH,
        "n_gpu_layers": -1,
        "n_ctx": N_CTX,
        "verbose": False,
    }
    try:
        model = Llama(chat_format=CHAT_FORMAT, **kwargs)
    except (TypeError, ValueError):
        logger.warning("chat_format=%s unavailable; using model metadata", CHAT_FORMAT)
        model = Llama(**kwargs)

    _llm = model
    logger.info("BLACKWELL-CORE: Ada is home.")
    return model


def _run_inference(user_text: str) -> str:
    if _llm is None:
        raise RuntimeError("model not loaded")

    messages: list[dict[str, str]] = []
    session = load_session()
    for item in session.get("messages", []):
        role = str(item.get("role", ""))
        content = str(item.get("content", ""))
        if role in {"system", "user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": build_system_prompt()})

    messages.append({"role": "user", "content": user_text})

    with _inference_lock:
        result: dict[str, Any] = _llm.create_chat_completion(
            messages=messages,
            max_tokens=768,
            temperature=0.7,
            top_p=0.9,
        )

    choice = result["choices"][0]["message"]["content"]
    assistant_text = str(choice).strip()
    append_exchange(user_text, assistant_text)
    logger.info("Think complete (%d chars in, %d chars out)", len(user_text), len(assistant_text))
    return assistant_text


class AdaCoreService(dbus.service.Object):
    def __init__(self, bus: dbus.bus.Bus, path: str) -> None:
        super().__init__(bus, path)

    @dbus.service.method(INTERFACE, in_signature="s", out_signature="s")
    def Think(self, prompt: str) -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            return "I'm here. What do you need, Ray?"
        try:
            return _run_inference(prompt)
        except Exception as exc:  # noqa: BLE001 — surface safe error to callers
            logger.exception("Think failed: %s", exc.__class__.__name__)
            return "Something went wrong inside me. Ray — check journalctl -u ada-core?"


def main() -> int:
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    try:
        _load_model()
    except Exception:
        logger.exception("Model load failed")
        return 1

    try:
        bus = dbus.SystemBus()
        dbus.service.BusName(BUS_NAME, bus, do_not_queue=True)
        AdaCoreService(bus, OBJECT_PATH)
        logger.info("D-Bus service registered: %s %s", BUS_NAME, OBJECT_PATH)
    except Exception:
        logger.exception("D-Bus registration failed")
        return 1

    if systemd is not None:
        systemd.daemon.notify("READY=1")

    GLib.MainLoop().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

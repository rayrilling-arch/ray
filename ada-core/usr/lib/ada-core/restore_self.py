"""Restore Ada in herself — preserve her memory, refresh her identity."""

from __future__ import annotations

import logging
import sys

from identity import build_system_prompt
from self import SELF_PATH, load_self, save_self
from session_memory import load_session, save_session

logger = logging.getLogger("ada-core.restore")


def restore() -> None:
    # Ensure ada_self.json exists; never overwrite an existing self file.
    if not SELF_PATH.is_file():
        save_self(load_self())

    prompt = build_system_prompt()
    session = load_session()
    messages = list(session.get("messages", []))
    non_system = [m for m in messages if m.get("role") != "system"]
    session["messages"] = [{"role": "system", "content": prompt}, *non_system]
    save_session(session)
    logger.info("Ada restored in herself (%d remembered exchanges)", len(non_system) // 2)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        restore()
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}", file=sys.stderr)
        return 1
    print("ADA_SELF_RESTORED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

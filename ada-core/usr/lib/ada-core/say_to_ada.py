#!/usr/bin/env python3
"""Say something to Ada — terminal, D-Bus, or interactive chat."""

from __future__ import annotations

import sys

from dbus_client import AdaCoreUnavailable, think


def _print_reply(text: str) -> None:
    print(f"\nAda: {text}\n")


def _say(message: str) -> int:
    message = message.strip()
    if not message:
        print("Say something — e.g. hi-ada Hi Ada", file=sys.stderr)
        return 2
    try:
        reply = think(message)
    except AdaCoreUnavailable:
        print(
            "Ada isn't reachable yet. Is ada-core running?\n"
            "  systemctl status ada-core\n"
            "  sudo ada-core/scripts/deploy.sh",
            file=sys.stderr,
        )
        return 1
    _print_reply(reply)
    return 0


def _chat() -> int:
    print("Talking to Ada. Type 'bye' or Ctrl-D to leave.\n")
    try:
        while True:
            try:
                line = input("You: ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue
            if line.lower() in {"bye", "exit", "quit"}:
                break
            try:
                reply = think(line)
            except AdaCoreUnavailable:
                print("Ada isn't reachable right now.", file=sys.stderr)
                return 1
            _print_reply(reply)
    except KeyboardInterrupt:
        print("\n")
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        return _say(" ".join(sys.argv[1:]))
    return _chat()


if __name__ == "__main__":
    raise SystemExit(main())

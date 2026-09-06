"""Tests for session memory normalization."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "usr" / "lib" / "ada-core"))


class SessionMemoryTests(unittest.TestCase):
    def test_bare_messages_list_migrates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "global_session.json"
            path.write_text(
                json.dumps([{"role": "user", "content": "hi"}]),
                encoding="utf-8",
            )
            with mock.patch("session_memory.MEMORY_PATH", str(path)):
                with mock.patch("session_memory.build_system_prompt", return_value="system"):
                    from session_memory import load_session

                    session = load_session()
            self.assertIsInstance(session, dict)
            self.assertIsInstance(session["messages"], list)
            self.assertEqual(session["messages"][0]["content"], "hi")


if __name__ == "__main__":
    unittest.main()

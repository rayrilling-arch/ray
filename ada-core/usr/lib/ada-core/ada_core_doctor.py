#!/usr/bin/env python3
"""Ada Core doctor — diagnose why hi-ada / D-Bus / TUI fail on HELM."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

MODEL_DIR = Path("/var/lib/ada-core/models")
VENV_PYTHON = Path("/usr/lib/ada-core/venv/bin/python3")
MEMORY_DIR = Path("/var/lib/ada-core/memory")

FAILURES = 0


def ok(msg: str) -> None:
    print(f"  OK   {msg}")


def fail(msg: str) -> None:
    global FAILURES
    FAILURES += 1
    print(f"  FAIL {msg}")


def warn(msg: str) -> None:
    print(f"  WARN {msg}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode, out.strip()
    except OSError as exc:
        return 1, str(exc)


def main() -> int:
    section("Services")
    for unit in ("ada-core.service", "ada-api-bridge.service", "ada-telegram.service"):
        code, out = run(["systemctl", "is-active", unit])
        if code == 0:
            ok(f"{unit} active")
        else:
            fail(f"{unit} not active")

    section("GPU / Ollama conflict")
    code, out = run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"])
    if code != 0:
        warn("nvidia-smi unavailable")
    elif not out:
        ok("GPU compute apps: none")
    else:
        warn(f"GPU in use: {out}")
        if "ollama" in out.lower():
            fail("Ollama is holding the GPU — run: sudo systemctl stop ollama")

    section("Python venv + llama-cpp")
    if not VENV_PYTHON.is_file():
        fail(f"venv missing at {VENV_PYTHON} — run: sudo ada-core/scripts/install.sh")
    else:
        ok("venv exists")
        code, out = run([str(VENV_PYTHON), "-c", "from llama_cpp import Llama; print('llama_cpp OK')"])
        if code == 0:
            ok("llama-cpp-python importable")
        else:
            fail("llama-cpp-python not installed in venv (Ada cannot start)")
            print(out)

    section("Model file")
    sys.path.insert(0, "/usr/lib/ada-core")
    try:
        from identity import MODEL_PATH  # noqa: WPS433

        path = Path(MODEL_PATH)
        if path.is_file():
            ok(f"model: {path} ({path.stat().st_size // (1024**2)} MiB)")
        else:
            fail(f"model missing: {path}")
            if MODEL_DIR.is_dir():
                ggufs = sorted(MODEL_DIR.glob("*.gguf"))
                if ggufs:
                    warn("found: " + ", ".join(p.name for p in ggufs))
                else:
                    fail(f"no .gguf files in {MODEL_DIR}")
    except Exception as exc:
        fail(f"could not resolve model path: {exc.__class__.__name__}")

    section("Memory + identity")
    self_file = MEMORY_DIR / "ada_self.json"
    session_file = MEMORY_DIR / "global_session.json"
    if self_file.is_file():
        ok("ada_self.json exists")
    else:
        fail("ada_self.json missing")
    if session_file.is_file():
        ok("global_session.json exists")
    else:
        warn("global_session.json missing (will be created)")

    section("D-Bus Think")
    code, out = run(
        [
            "gdbus",
            "call",
            "--system",
            "--dest",
            "org.popos.AdaCore",
            "--object-path",
            "/org/popos/AdaCore",
            "--method",
            "org.popos.AdaCore.Think",
            "ping",
        ]
    )
    if code == 0:
        ok("D-Bus Think responds")
        print(f"       {out[:200]}")
    else:
        fail("D-Bus Think failed — ada-core not serving")
        print(out)

    section("Recent ada-core errors")
    _, journal = run(["journalctl", "-u", "ada-core", "-n", "25", "--no-pager"])
    if journal:
        for line in journal.splitlines()[-12:]:
            print(f"  {line}")

    if "--load-test" in sys.argv:
        section("Model load test (as ada user, may take minutes)")
        code, out = run(
            [
                "sudo",
                "-u",
                "ada",
                "env",
                f"PYTHONPATH=/usr/lib/ada-core",
                str(VENV_PYTHON),
                "-c",
                (
                    "from supervisor import _load_model; "
                    "m=_load_model(); "
                    "r=m.create_chat_completion(messages=[{'role':'user','content':'hi'}], max_tokens=8); "
                    "print('LOAD_OK', r['choices'][0]['message']['content'][:80])"
                ),
            ]
        )
        if code == 0 and "LOAD_OK" in out:
            ok("model load + inference test passed")
            print(f"       {out}")
        else:
            fail("model load test failed")
            print(out)

    section("Summary")
    if FAILURES:
        print(f"  {FAILURES} failure(s) — Ada Core is not healthy.")
        print("  Try: sudo ada-core/scripts/repair-ada-core.sh")
        return 1
    print("  Ada Core looks healthy. If OpenClaw web/TUI still fail, run fix-openclaw-ada.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

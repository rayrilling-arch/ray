"""Resolve Ada's Qwen 3.5 model on HELM."""

from __future__ import annotations

import os
from pathlib import Path

MODEL_DIR = Path("/var/lib/ada-core/models")
MODEL_FAMILY = "Qwen 3.5"
CHAT_FORMAT = "qwen3.5"
DEFAULT_MODEL_NAME = "Qwen3.5-9B-Q4_K_M.gguf"

MODEL_CANDIDATES = (
    "Qwen3.5-9B-Q4_K_M.gguf",
    "Qwen3.5-9B-Instruct-Q4_K_M.gguf",
    "qwen3.5-9b-q4_k_m.gguf",
    "Qwen_Qwen3.5-9B-Q4_K_M.gguf",
    "Qwen3.5-4B-Q4_K_M.gguf",
    # legacy fallback if Qwen not yet downloaded
    "llama-3-8b-instruct-q4_k_m.gguf",
)


def resolve_model_path() -> Path:
    override = os.environ.get("ADA_MODEL_PATH", "").strip()
    if override:
        path = Path(override)
        if path.is_file():
            return path

    for name in MODEL_CANDIDATES:
        path = MODEL_DIR / name
        if path.is_file():
            return path

    for path in sorted(MODEL_DIR.glob("*.gguf")):
        lowered = path.name.lower()
        if "qwen" in lowered and "3.5" in lowered.replace("_", "."):
            return path

    return MODEL_DIR / DEFAULT_MODEL_NAME

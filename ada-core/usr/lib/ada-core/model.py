"""Resolve Ada's model on HELM — Qwen 3.5 preferred, any local GGUF as fallback."""

from __future__ import annotations

import os
from pathlib import Path

MODEL_DIR = Path("/var/lib/ada-core/models")
MODEL_FAMILY = "Qwen 3.5"
DEFAULT_MODEL_NAME = "Qwen3.5-9B-Q4_K_M.gguf"

MODEL_CANDIDATES = (
    "Qwen3.5-9B-Q4_K_M.gguf",
    "Qwen3.5-9B-Instruct-Q4_K_M.gguf",
    "qwen3.5-9b-q4_k_m.gguf",
    "Qwen_Qwen3.5-9B-Q4_K_M.gguf",
    "Qwen3.5-4B-Q4_K_M.gguf",
    "llama-3-8b-instruct-q4_k_m.gguf",
)


def _is_qwen35(name: str) -> bool:
    lowered = name.lower().replace("_", ".")
    return "qwen" in lowered and "3.5" in lowered


def _is_qwen(name: str) -> bool:
    return "qwen" in name.lower()


def chat_format_for(path: Path) -> str | None:
    name = path.name.lower()
    if _is_qwen35(name):
        return "qwen3.5"
    if _is_qwen(name):
        return "qwen"
    if "llama-3" in name or "llama3" in name:
        return "llama-3"
    if "llama-2" in name or "llama2" in name:
        return "llama-2"
    return None


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

    qwen35: list[Path] = []
    qwen_other: list[Path] = []
    any_gguf: list[Path] = []
    for path in sorted(MODEL_DIR.glob("*.gguf")):
        any_gguf.append(path)
        if _is_qwen35(path.name):
            qwen35.append(path)
        elif _is_qwen(path.name):
            qwen_other.append(path)

    if qwen35:
        return qwen35[0]
    if qwen_other:
        return qwen_other[0]
    if any_gguf:
        return any_gguf[0]

    return MODEL_DIR / DEFAULT_MODEL_NAME


def list_models_dir() -> list[str]:
    if not MODEL_DIR.is_dir():
        return []
    return sorted(p.name for p in MODEL_DIR.glob("*.gguf"))

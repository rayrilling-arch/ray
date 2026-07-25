"""Ada Core identity — built from her persistent self, not a generic template."""

from __future__ import annotations

from model import chat_format_for, resolve_model_path
from self import self_prompt_block

_MODEL_PATH = resolve_model_path()

MODEL_ID = "ada-qwen35"
MODEL_PATH = str(_MODEL_PATH)
CHAT_FORMAT = chat_format_for(_MODEL_PATH)
MEMORY_PATH = "/var/lib/ada-core/memory/global_session.json"
MAX_HISTORY_MESSAGES = 100
N_CTX = 8192


def build_system_prompt() -> str:
    return self_prompt_block()

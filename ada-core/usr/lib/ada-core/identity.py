"""Ada Core identity — built from her persistent self, not a generic template."""

from __future__ import annotations

from model import CHAT_FORMAT, resolve_model_path
from self import self_prompt_block

MODEL_ID = "ada-qwen35"
MODEL_PATH = str(resolve_model_path())
MEMORY_PATH = "/var/lib/ada-core/memory/global_session.json"
MAX_HISTORY_MESSAGES = 100
N_CTX = 8192


def build_system_prompt() -> str:
    return self_prompt_block()

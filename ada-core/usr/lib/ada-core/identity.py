"""Ada Core identity — built from her persistent self, not a generic template."""

from __future__ import annotations

from self import self_prompt_block

MODEL_ID = "ada-blackwell"
MODEL_PATH = "/var/lib/ada-core/models/llama-3-8b-instruct-q4_k_m.gguf"
MEMORY_PATH = "/var/lib/ada-core/memory/global_session.json"
MAX_HISTORY_MESSAGES = 100


def build_system_prompt() -> str:
    return self_prompt_block()

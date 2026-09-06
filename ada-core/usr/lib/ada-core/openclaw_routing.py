"""Rewire OpenClaw from Ollama Cloud to local Ada Core (ada-api-bridge)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

ADA_LOCAL_API = "http://127.0.0.1:8000/v1"
ADA_MODEL_ID = "ada-qwen35"
ADA_MODEL_REF = f"openai/{ADA_MODEL_ID}"
ADA_PROVIDER = "openai"

# Models that must not be used — they hit Ollama Cloud and fail without cloud auth.
BLOCKED_MODEL_REFS = frozenset(
    {
        "ollama/qwen3.5:cloud",
        "qwen3.5:cloud",
        "ollama/qwen3.5-cloud",
    }
)


def _is_blocked_model(value: object) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.strip().lower()
    if lowered in BLOCKED_MODEL_REFS:
        return True
    if ":cloud" in lowered and ("ollama" in lowered or "qwen" in lowered):
        return True
    return False


def _replace_model_value(value: object) -> tuple[object, bool]:
    if isinstance(value, str):
        if _is_blocked_model(value):
            return ADA_MODEL_REF, True
        return value, False
    if isinstance(value, dict):
        changed = False
        updated = {}
        for key, item in value.items():
            new_item, item_changed = _replace_model_value(item)
            updated[key] = new_item
            changed = changed or item_changed
        return updated, changed
    if isinstance(value, list):
        changed = False
        updated_list: list[Any] = []
        for item in value:
            new_item, item_changed = _replace_model_value(item)
            updated_list.append(new_item)
            changed = changed or item_changed
        return updated_list, changed
    return value, False


def _ensure_ada_openai_provider(cfg: dict[str, Any]) -> bool:
    """Register ada-api-bridge under models.providers.openai (OpenClaw schema)."""
    changed = False
    models = cfg.setdefault("models", {})
    if not isinstance(models, dict):
        return False

    providers = models.setdefault("providers", {})
    if not isinstance(providers, dict):
        return False

    openai = providers.get("openai")
    if not isinstance(openai, dict):
        openai = {}
        providers["openai"] = openai
        changed = True

    if openai.get("baseUrl") != ADA_LOCAL_API:
        openai["baseUrl"] = ADA_LOCAL_API
        changed = True
    if openai.get("apiKey") != "ada-local":
        openai["apiKey"] = "ada-local"
        changed = True
    if openai.get("api") != "openai-completions":
        openai["api"] = "openai-completions"
        changed = True

    model_entries = openai.get("models")
    if not isinstance(model_entries, list):
        model_entries = []
        openai["models"] = model_entries
        changed = True

    ada_entry = None
    for entry in model_entries:
        if isinstance(entry, dict) and entry.get("id") == ADA_MODEL_ID:
            ada_entry = entry
            break

    if ada_entry is None:
        model_entries.append(
            {
                "id": ADA_MODEL_ID,
                "name": "Ada (Qwen 3.5 local)",
                "reasoning": False,
                "input": ["text"],
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                "contextTokens": 8192,
                "maxTokens": 8192,
            }
        )
        changed = True

    # Legacy top-level providers key (older configs) — mirror for safety.
    legacy = cfg.get("providers")
    if isinstance(legacy, dict):
        legacy_openai = legacy.get("openai")
        if isinstance(legacy_openai, dict):
            if legacy_openai.get("baseUrl") != ADA_LOCAL_API:
                legacy_openai["baseUrl"] = ADA_LOCAL_API
                changed = True

    return changed


def _rewire_agents(cfg: dict[str, Any]) -> bool:
    changed = False
    agents = cfg.get("agents")
    if not isinstance(agents, dict):
        return False

    defaults = agents.get("defaults")
    if isinstance(defaults, dict) and "model" in defaults:
        new_model, model_changed = _replace_model_value(defaults["model"])
        if model_changed:
            defaults["model"] = new_model
            changed = True
        elif isinstance(defaults.get("model"), dict):
            primary = defaults["model"].get("primary")
            if primary is None or _is_blocked_model(str(primary)):
                defaults["model"]["primary"] = ADA_MODEL_REF
                changed = True

    entries = agents.get("list")
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            agent_id = str(entry.get("id", ""))
            if "model" in entry:
                new_model, model_changed = _replace_model_value(entry["model"])
                if model_changed:
                    entry["model"] = new_model
                    changed = True
                elif isinstance(entry.get("model"), str):
                    model_str = entry["model"]
                    if _is_blocked_model(model_str) or (
                        "ollama" in model_str.lower() and model_str != ADA_MODEL_REF
                    ):
                        entry["model"] = ADA_MODEL_REF
                        changed = True
            if agent_id in {"ada", "main", "default"}:
                if entry.get("provider") != ADA_PROVIDER:
                    entry["provider"] = ADA_PROVIDER
                    changed = True
                model_val = entry.get("model")
                if isinstance(model_val, str) and model_val != ADA_MODEL_REF:
                    if _is_blocked_model(model_val) or "ollama" in model_val.lower():
                        entry["model"] = ADA_MODEL_REF
                        changed = True
                elif model_val is None:
                    entry["model"] = ADA_MODEL_REF
                    changed = True

    return changed


def fix_openclaw_routing(cfg: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return updated config and whether anything changed."""
    updated = deepcopy(cfg)
    changed = _ensure_ada_openai_provider(updated)
    changed = _rewire_agents(updated) or changed
    return updated, changed


def find_blocked_model_refs(cfg: dict[str, Any]) -> list[str]:
    """Return any blocked model refs still present after scanning JSON-ish structure."""
    found: list[str] = []

    def walk(value: object, path: str) -> None:
        if isinstance(value, str):
            if _is_blocked_model(value):
                found.append(f"{path}={value}")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else str(key))
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(cfg, "")
    return found

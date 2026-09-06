"""Audit and fix OpenClaw plugin + per-agent overrides that hijack Ada routing."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from openclaw_routing import (
    ADA_MODEL_REF,
    find_blocked_model_refs,
    fix_openclaw_routing,
)

# Plugins known to re-introduce Ollama Cloud or override model routing.
OLLAMA_PLUGIN_IDS = (
    "ollama",
    "ollama-cloud",
    "ollama-provider",
)

WORKSPACE_MODEL_GLOBS = (
    "models.json",
    "workspace/models.json",
    "workspace/agents/*/models.json",
)


@dataclass
class AuditIssue:
    severity: str  # fail | warn | info
    source: str
    message: str


@dataclass
class AuditReport:
    issues: list[AuditIssue] = field(default_factory=list)

    def add(self, severity: str, source: str, message: str) -> None:
        self.issues.append(AuditIssue(severity, source, message))


def resolve_openclaw_home() -> Path:
    return Path(os.environ.get("OPENCLAW_HOME", "/home/adarilling/.openclaw"))


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _backup_file(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, backup)
    return backup


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def iter_workspace_model_files(home: Path) -> list[Path]:
    found: list[Path] = []
    candidates = [
        home / "models.json",
        home / "workspace" / "models.json",
    ]
    agents_root = home / "workspace" / "agents"
    if agents_root.is_dir():
        for agent_dir in sorted(agents_root.iterdir()):
            if agent_dir.is_dir():
                candidate = agent_dir / "models.json"
                if candidate.is_file():
                    candidates.append(candidate)
    for path in candidates:
        if path.is_file():
            found.append(path)
    return found


def _audit_plugins(cfg: dict[str, Any], report: AuditReport, source: str) -> None:
    plugins = cfg.get("plugins")
    if not isinstance(plugins, dict):
        return
    entries = plugins.get("entries")
    if not isinstance(entries, dict):
        return

    for plugin_id, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        lowered = plugin_id.lower()
        if lowered not in OLLAMA_PLUGIN_IDS and "ollama" not in lowered:
            continue

        enabled = entry.get("enabled", True)
        config = entry.get("config") if isinstance(entry.get("config"), dict) else {}
        discovery = config.get("discovery") if isinstance(config.get("discovery"), dict) else {}
        discovery_on = discovery.get("enabled", True)

        if enabled is not False:
            report.add(
                "warn",
                source,
                f"plugin '{plugin_id}' is enabled — can inject Ollama/cloud models",
            )
        if discovery_on is not False and lowered == "ollama":
            report.add(
                "warn",
                source,
                f"plugin '{plugin_id}' discovery is enabled — may add qwen3.5:cloud",
            )


def _audit_ollama_provider(cfg: dict[str, Any], report: AuditReport, source: str) -> None:
    models = cfg.get("models")
    if not isinstance(models, dict):
        return
    providers = models.get("providers")
    if not isinstance(providers, dict):
        return

    for provider_id, provider in providers.items():
        if not isinstance(provider, dict):
            continue
        if "ollama" not in provider_id.lower():
            continue
        base_url = str(provider.get("baseUrl", "")).lower()
        if "ollama.com" in base_url:
            report.add(
                "fail",
                source,
                f"provider '{provider_id}' baseUrl points at Ollama Cloud ({provider.get('baseUrl')})",
            )
        model_entries = provider.get("models")
        if isinstance(model_entries, list):
            for entry in model_entries:
                model_id = ""
                if isinstance(entry, dict):
                    model_id = str(entry.get("id", ""))
                elif isinstance(entry, str):
                    model_id = entry
                if ":cloud" in model_id.lower():
                    report.add(
                        "fail",
                        source,
                        f"provider '{provider_id}' lists cloud model id '{model_id}'",
                    )


def audit_config_dict(cfg: dict[str, Any], source: str, report: AuditReport) -> None:
    for ref in find_blocked_model_refs(cfg):
        report.add("fail", source, f"blocked model ref: {ref}")
    _audit_plugins(cfg, report, source)
    _audit_ollama_provider(cfg, report, source)

    defaults = (cfg.get("agents") or {}).get("defaults") if isinstance(cfg.get("agents"), dict) else {}
    if isinstance(defaults, dict):
        model_map = defaults.get("models")
        if isinstance(model_map, dict):
            for key in model_map:
                if "ollama" in str(key).lower() and "ada-qwen35" not in str(key).lower():
                    report.add("warn", source, f"agents.defaults.models key still Ollama: {key}")


def audit_openclaw(home: Path | None = None) -> AuditReport:
    home = home or resolve_openclaw_home()
    report = AuditReport()

    main_config = home / "openclaw.json"
    if not main_config.is_file():
        report.add("fail", str(main_config), "missing openclaw.json")
        return report

    main_data = _load_json(main_config)
    if main_data is None:
        report.add("fail", str(main_config), "could not parse openclaw.json")
        return report

    audit_config_dict(main_data, str(main_config), report)

    for path in iter_workspace_model_files(home):
        data = _load_json(path)
        if data is None:
            report.add("warn", str(path), "could not parse models override file")
            continue
        audit_config_dict(data, str(path), report)

    return report


def _neutralize_plugins(cfg: dict[str, Any]) -> bool:
    changed = False
    plugins = cfg.setdefault("plugins", {})
    if not isinstance(plugins, dict):
        return False
    entries = plugins.setdefault("entries", {})
    if not isinstance(entries, dict):
        return False

    for plugin_id in list(entries.keys()):
        lowered = plugin_id.lower()
        if lowered not in OLLAMA_PLUGIN_IDS and "ollama" not in lowered:
            continue
        entry = entries.get(plugin_id)
        if not isinstance(entry, dict):
            continue

        if lowered in {"ollama-cloud", "ollama-provider"}:
            if entry.get("enabled") is not False:
                entry["enabled"] = False
                changed = True
            continue

        if lowered == "ollama":
            config = entry.setdefault("config", {})
            if not isinstance(config, dict):
                config = {}
                entry["config"] = config
            discovery = config.setdefault("discovery", {})
            if not isinstance(discovery, dict):
                discovery = {}
                config["discovery"] = discovery
            if discovery.get("enabled") is not False:
                discovery["enabled"] = False
                changed = True
            node_inference = config.setdefault("nodeInference", {})
            if isinstance(node_inference, dict) and node_inference.get("enabled") is not False:
                node_inference["enabled"] = False
                changed = True

    return changed


def _fix_ollama_providers(cfg: dict[str, Any]) -> bool:
    changed = False
    models = cfg.get("models")
    if not isinstance(models, dict):
        return False
    providers = models.get("providers")
    if not isinstance(providers, dict):
        return False

    for provider_id, provider in list(providers.items()):
        if not isinstance(provider, dict) or "ollama" not in provider_id.lower():
            continue
        base_url = str(provider.get("baseUrl", "")).lower()
        if "ollama.com" in base_url or provider_id.lower() == "ollama-cloud":
            providers.pop(provider_id, None)
            changed = True
            continue

        model_entries = provider.get("models")
        if isinstance(model_entries, list):
            kept: list[Any] = []
            list_changed = False
            for entry in model_entries:
                model_id = ""
                if isinstance(entry, dict):
                    model_id = str(entry.get("id", ""))
                elif isinstance(entry, str):
                    model_id = entry
                if ":cloud" in model_id.lower():
                    list_changed = True
                    continue
                kept.append(entry)
            if list_changed:
                provider["models"] = kept
                changed = True

    return changed


def _fix_defaults_model_map(cfg: dict[str, Any]) -> bool:
    changed = False
    agents = cfg.get("agents")
    if not isinstance(agents, dict):
        return False
    defaults = agents.get("defaults")
    if not isinstance(defaults, dict):
        return False
    model_map = defaults.get("models")
    if not isinstance(model_map, dict):
        return False

    new_map: dict[str, Any] = {}
    for key, value in model_map.items():
        key_str = str(key)
        if ":cloud" in key_str.lower() or (
            "ollama" in key_str.lower() and "ada-qwen35" not in key_str.lower()
        ):
            new_map[ADA_MODEL_REF] = value
            changed = True
        else:
            new_map[key_str] = value
    if changed:
        defaults["models"] = new_map
    return changed


def _pin_defaults_model(cfg: dict[str, Any]) -> bool:
    changed = False
    agents = cfg.setdefault("agents", {})
    if not isinstance(agents, dict):
        return False
    defaults = agents.setdefault("defaults", {})
    if not isinstance(defaults, dict):
        return False

    model = defaults.get("model")
    if isinstance(model, str):
        if model != ADA_MODEL_REF:
            defaults["model"] = ADA_MODEL_REF
            changed = True
    elif isinstance(model, dict):
        if model.get("primary") != ADA_MODEL_REF:
            model["primary"] = ADA_MODEL_REF
            changed = True
        fallbacks = model.get("fallbacks")
        if isinstance(fallbacks, list):
            cleaned = [ADA_MODEL_REF if "ollama" in str(item).lower() else item for item in fallbacks]
            cleaned = [item for item in cleaned if ":cloud" not in str(item).lower()]
            if cleaned != fallbacks:
                model["fallbacks"] = cleaned
                changed = True
    else:
        defaults["model"] = {"primary": ADA_MODEL_REF, "fallbacks": []}
        changed = True

    policy = defaults.setdefault("modelPolicy", {})
    if isinstance(policy, dict):
        allow = policy.get("allow")
        if allow is None:
            policy["allow"] = [ADA_MODEL_REF]
            changed = True
        elif isinstance(allow, list):
            cleaned_allow = [ADA_MODEL_REF]
            if allow != cleaned_allow:
                policy["allow"] = cleaned_allow
                changed = True

    return changed


def fix_config_dict(cfg: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    updated, changed = fix_openclaw_routing(cfg)
    changed = _neutralize_plugins(updated) or changed
    changed = _fix_ollama_providers(updated) or changed
    changed = _fix_defaults_model_map(updated) or changed
    changed = _pin_defaults_model(updated) or changed

    models = updated.setdefault("models", {})
    if isinstance(models, dict) and models.get("mode") != "merge":
        models["mode"] = "merge"
        changed = True

    return updated, changed


def fix_json_path(path: Path, write: bool = True) -> tuple[bool, Path | None]:
    data = _load_json(path)
    if data is None:
        return False, None
    fixed, changed = fix_config_dict(data)
    if not changed or not write:
        return changed, None
    backup = _backup_file(path)
    _write_json(path, fixed)
    return True, backup


def fix_all_openclaw(home: Path | None = None) -> list[str]:
    """Fix openclaw.json and all workspace model override files. Returns log lines."""
    home = home or resolve_openclaw_home()
    logs: list[str] = []

    targets = [home / "openclaw.json", *iter_workspace_model_files(home)]
    seen: set[Path] = set()
    for path in targets:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        changed, backup = fix_json_path(path, write=True)
        if changed:
            logs.append(f"FIXED {path} backup={backup}")

    return logs


def format_report(report: AuditReport) -> str:
    if not report.issues:
        return "No OpenClaw routing/plugin issues detected."
    lines = ["OpenClaw audit:"]
    for issue in report.issues:
        lines.append(f"  [{issue.severity.upper()}] {issue.source}: {issue.message}")
    return "\n".join(lines)

#!/usr/bin/env python3
"""Unit tests for Ada Core OpenClaw routing (run without HELM)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "usr" / "lib" / "ada-core"))

from openclaw_audit import audit_openclaw, fix_all_openclaw, fix_config_dict
from openclaw_routing import ADA_MODEL_REF, find_blocked_model_refs, fix_openclaw_routing


class OpenClawRoutingTests(unittest.TestCase):
    def test_blocked_cloud_model_replaced(self) -> None:
        cfg = {
            "agents": {
                "defaults": {"model": {"primary": "ollama/qwen3.5:cloud"}},
                "list": [{"id": "research", "model": "ollama/qwen3.5:cloud"}],
            }
        }
        fixed, changed = fix_config_dict(cfg)
        self.assertTrue(changed)
        self.assertEqual(fixed["agents"]["defaults"]["model"]["primary"], ADA_MODEL_REF)
        self.assertEqual(fixed["agents"]["list"][0]["model"], ADA_MODEL_REF)
        self.assertEqual(find_blocked_model_refs(fixed), [])

    def test_ollama_plugin_neutralized(self) -> None:
        cfg = {
            "plugins": {
                "entries": {
                    "ollama": {"enabled": True, "config": {"discovery": {"enabled": True}}},
                    "ollama-cloud": {"enabled": True},
                }
            }
        }
        fixed, changed = fix_config_dict(cfg)
        self.assertTrue(changed)
        self.assertFalse(fixed["plugins"]["entries"]["ollama-cloud"]["enabled"])
        self.assertFalse(fixed["plugins"]["entries"]["ollama"]["config"]["discovery"]["enabled"])

    def test_openai_provider_points_at_ada_bridge(self) -> None:
        fixed, _ = fix_openclaw_routing({})
        openai = fixed["models"]["providers"]["openai"]
        self.assertEqual(openai["baseUrl"], "http://127.0.0.1:8000/v1")
        self.assertEqual(openai["api"], "openai-completions")

    def test_workspace_agent_models_json_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agent_dir = home / "workspace" / "agents" / "ada"
            agent_dir.mkdir(parents=True)
            models_path = agent_dir / "models.json"
            models_path.write_text(
                json.dumps({"agents": {"defaults": {"model": "ollama/qwen3.5:cloud"}}}),
                encoding="utf-8",
            )
            (home / "openclaw.json").write_text(
                json.dumps({"agents": {"defaults": {"model": "ollama/qwen3.5:cloud"}}}),
                encoding="utf-8",
            )
            logs = fix_all_openclaw(home)
            self.assertTrue(any("models.json" in line for line in logs))
            report = audit_openclaw(home)
            fails = [i for i in report.issues if i.severity == "fail"]
            self.assertEqual(fails, [])


if __name__ == "__main__":
    unittest.main()

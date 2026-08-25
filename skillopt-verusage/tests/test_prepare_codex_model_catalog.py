from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "prepare_codex_model_catalog.py"
)
SPEC = importlib.util.spec_from_file_location("prepare_codex_model_catalog", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_normalize_model_entry_fills_current_codex_required_fields() -> None:
    entry = MODULE.normalize_model_entry(
        {
            "slug": "deepseek-v4-pro",
            "supports_parallel_tool_calls": True,
            "tool_mode": "code_mode_only",
            "use_responses_lite": True,
        }
    )
    assert entry["supports_parallel_tool_calls"] is True
    assert entry["prefer_websockets"] is False
    assert entry["auto_compact_token_limit"] is None
    assert entry["reasoning_summary_format"] == "experimental"
    assert entry["minimal_client_version"] == "0.144.0"
    assert entry["available_in_plans"] == []
    assert entry["supports_reasoning_summaries"] is True
    assert entry["tool_mode"] == "direct"
    assert entry["use_responses_lite"] is False

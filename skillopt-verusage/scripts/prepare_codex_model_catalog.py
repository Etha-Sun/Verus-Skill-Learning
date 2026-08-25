from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize_model_entry(entry: dict) -> dict:
    """Fill fields required by the pinned Codex custom-catalog schema.

    The remote models cache can omit fields that the local Codex binary
    requires when parsing an explicit ``model_catalog_json``. Keep upstream
    capabilities when present and use conservative bridge defaults otherwise.
    """
    normalized = dict(entry)
    defaults = {
        "prefer_websockets": False,
        "supports_parallel_tool_calls": False,
        "auto_compact_token_limit": None,
        "reasoning_summary_format": "experimental",
        "minimal_client_version": "0.144.0",
        "available_in_plans": [],
        "supports_reasoning_summaries": True,
    }
    for key, value in defaults.items():
        normalized.setdefault(key, value)
    normalized["tool_mode"] = "direct"
    normalized["use_responses_lite"] = False
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--template-slug", default="deepseek-v4-pro")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--context-window", type=int, required=True)
    parser.add_argument("--default-reasoning-level", default="high")
    args = parser.parse_args()

    catalog = json.loads(args.input.read_text(encoding="utf-8"))
    templates = [
        entry
        for entry in catalog.get("models") or []
        if entry.get("slug") == args.template_slug
    ]
    if len(templates) != 1:
        raise ValueError(
            f"expected one {args.template_slug!r} template, found {len(templates)}"
        )
    entry = normalize_model_entry(templates[0])
    entry.update(
        {
            "slug": args.slug,
            "display_name": args.display_name,
            "context_window": args.context_window,
            "max_context_window": args.context_window,
            "default_reasoning_level": args.default_reasoning_level,
        }
    )
    output = {"models": [entry]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

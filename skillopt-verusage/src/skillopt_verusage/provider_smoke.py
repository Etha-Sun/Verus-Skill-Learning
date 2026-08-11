from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from openai import OpenAI

from skillopt_verusage.runner import FLASH_RATES_USD_PER_MILLION
from skillopt_verusage.skill_proxy import _usage_dict


def _external_empty(path: Path) -> Path:
    root_text = os.environ.get("VERUS_SKILL_RUN_ROOT", "")
    if not root_text:
        raise ValueError("VERUS_SKILL_RUN_ROOT is not configured")
    root = Path(root_text).resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"output must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    if resolved.exists() and any(resolved.iterdir()):
        raise ValueError(f"output must be empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-v4-flash")
    args = parser.parse_args()
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    out_dir = _external_empty(args.out_dir)
    client = OpenAI(
        api_key=key,
        base_url="https://api.deepseek.com",
        max_retries=0,
        timeout=60,
    )
    started = time.monotonic()
    models = client.models.list()
    model_ids = sorted(str(model.id) for model in models.data)
    if args.model not in model_ids:
        raise RuntimeError(f"required model is unavailable: {args.model}")
    response = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": "Reply with exactly OK."}],
        max_tokens=8,
        temperature=0,
        extra_body={"thinking": {"type": "disabled"}},
    )
    usage = _usage_dict(response.usage)
    estimated_cost_usd = round(
        sum(
            usage[key_name] * rate / 1_000_000
            for key_name, rate in FLASH_RATES_USD_PER_MILLION.items()
        ),
        8,
    )
    result = {
        "status": "ok",
        "model": args.model,
        "required_model_listed": True,
        "response": str(response.choices[0].message.content or ""),
        "usage": usage,
        "estimated_cost_usd": estimated_cost_usd,
        "wall_seconds": time.monotonic() - started,
    }
    (out_dir / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

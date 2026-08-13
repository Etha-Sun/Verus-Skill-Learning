from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from skillopt_verusage.budget_guard import estimate_deepseek_cost, rates_for_model


TOKEN_KEYS = (
    "prompt_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
    "completion_tokens",
)


def _cost(totals: dict[str, Any], model: str) -> float:
    return estimate_deepseek_cost(totals, model)


def _target_usage(
    task_dir: Path,
    model: str,
) -> tuple[dict[str, Any], bool]:
    usage_path = task_dir / "usage.json"
    if usage_path.is_file():
        try:
            return json.loads(usage_path.read_text(encoding="utf-8")), True
        except json.JSONDecodeError:
            pass
    totals: dict[str, Any] = {"requests": 0, **{key: 0 for key in TOKEN_KEYS}}
    calls_path = task_dir / "target_calls.jsonl"
    for line in calls_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            call = json.loads(line)
        except json.JSONDecodeError:
            continue
        totals["requests"] += 1
        usage = call.get("usage") or {}
        for key in TOKEN_KEYS:
            totals[key] += int(usage.get(key, 0) or 0)
    totals["estimated_cost_usd"] = _cost(totals, model)
    return totals, False


def _optimizer_usage(run_root: Path, model: str) -> dict[str, Any]:
    rates = rates_for_model(model)
    codex_ledger = run_root / "optimizer_calls.jsonl"
    if codex_ledger.is_file():
        rows = [
            json.loads(line)
            for line in codex_ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        successful = [row for row in rows if row.get("status") == "success"]
        prompt = sum(
            int((row.get("usage") or {}).get("prompt_tokens", 0) or 0)
            for row in successful
        )
        completion = sum(
            int((row.get("usage") or {}).get("completion_tokens", 0) or 0)
            for row in successful
        )
        return {
            "source": "codex_optimizer_calls",
            "calls": len(successful),
            "failed_calls": len(rows) - len(successful),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "actual_metered_cost_usd": 0.0,
            "estimated_cost_usd_all_prompt_cache_miss": (
                prompt * rates["prompt_cache_miss_tokens"]
                + completion * rates["completion_tokens"]
            )
            / 1_000_000,
            "estimate_only": "DeepSeek-equivalent rate; optimizer used local Codex quota",
        }
    summary_path = run_root / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        total = dict((summary.get("token_summary") or {}).get("_total") or {})
        calls = int(total.get("calls", 0) or 0)
        prompt = int(total.get("prompt_tokens", 0) or 0)
        completion = int(total.get("completion_tokens", 0) or 0)
        return {
            "source": "final_summary",
            "calls": calls,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "estimated_cost_usd_all_prompt_cache_miss": (
                prompt * rates["prompt_cache_miss_tokens"]
                + completion
                * rates["completion_tokens"]
            )
            / 1_000_000,
        }

    history_path = run_root / "history.json"
    calls = prompt = completion = 0
    if history_path.is_file():
        history = json.loads(history_path.read_text(encoding="utf-8"))
        for record in history:
            for usage in (record.get("tokens") or {}).values():
                calls += int(usage.get("calls", 0) or 0)
                prompt += int(usage.get("prompt_tokens", 0) or 0)
                completion += int(usage.get("completion_tokens", 0) or 0)
    return {
        "source": "completed_step_history",
        "calls": calls,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "estimated_cost_usd_all_prompt_cache_miss": (
            prompt
            * rates["prompt_cache_miss_tokens"]
            + completion * rates["completion_tokens"]
        )
        / 1_000_000,
    }


def _target_model(run_root: Path) -> str:
    models: set[str] = set()
    for path in run_root.rglob("run_manifest.json"):
        try:
            model = str(json.loads(path.read_text(encoding="utf-8")).get("model") or "")
        except json.JSONDecodeError:
            continue
        if model:
            models.add(model)
    if len(models) > 1:
        raise ValueError(f"mixed target models in one run: {sorted(models)}")
    return next(iter(models), "deepseek-v4-flash")


def build_cost_ledger(run_root: Path) -> dict[str, Any]:
    run_root = run_root.resolve()
    model = _target_model(run_root)
    task_dirs = sorted(
        path.parent for path in run_root.rglob("target_calls.jsonl")
    )
    target: dict[str, Any] = {
        "task_ledgers": len(task_dirs),
        "completed_task_ledgers": 0,
        "partial_task_ledgers": 0,
        "requests": 0,
        **{key: 0 for key in TOKEN_KEYS},
    }
    by_phase: dict[str, dict[str, Any]] = {}
    bridge_path = run_root / "bridge_calls.jsonl"
    if bridge_path.is_file():
        rows = [
            json.loads(line)
            for line in bridge_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        task_ids: set[str] = set()
        for row in rows:
            task_id = str(row.get("task_id") or "")
            if task_id:
                task_ids.add(task_id)
            for attempt in row.get("attempts") or []:
                usage = attempt.get("usage")
                if not isinstance(usage, dict):
                    continue
                target["requests"] += 1
                for key in TOKEN_KEYS:
                    target[key] += int(usage.get(key, 0) or 0)
        target["task_ledgers"] = len(task_ids)
        target["completed_task_ledgers"] = len(task_ids)
        target["ledger_source"] = "codex_responses_bridge"
        by_phase["codex_bridge"] = {
            "tasks": len(task_ids),
            "requests": target["requests"],
            **{key: target[key] for key in TOKEN_KEYS},
        }
    for task_dir in task_dirs:
        usage, complete = _target_usage(task_dir, model)
        relative = task_dir.relative_to(run_root)
        phase = relative.parts[0] if relative.parts else "unknown"
        phase_totals = by_phase.setdefault(
            phase,
            {"tasks": 0, "requests": 0, **{key: 0 for key in TOKEN_KEYS}},
        )
        phase_totals["tasks"] += 1
        target["completed_task_ledgers" if complete else "partial_task_ledgers"] += 1
        for key in ("requests", *TOKEN_KEYS):
            value = int(usage.get(key, 0) or 0)
            target[key] += value
            phase_totals[key] += value
    target["estimated_cost_usd"] = _cost(target, model)
    for totals in by_phase.values():
        totals["estimated_cost_usd"] = _cost(totals, model)

    optimizer = _optimizer_usage(run_root, model)
    combined = target["estimated_cost_usd"] + optimizer[
        "estimated_cost_usd_all_prompt_cache_miss"
    ]
    return {
        "schema_version": "1",
        "model": model,
        "status": "complete" if (run_root / "summary.json").is_file() else "running",
        "target": target,
        "target_by_phase": by_phase,
        "optimizer": optimizer,
        "combined_estimated_cost_usd": combined,
        "optimizer_cache_assumption": "all prompt tokens treated as cache miss",
    }


def write_cost_ledger(run_root: Path) -> dict[str, Any]:
    ledger = build_cost_ledger(run_root)
    (run_root / "cost_ledger.json").write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    ledger = write_cost_ledger(args.run_root)
    print(json.dumps(ledger, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

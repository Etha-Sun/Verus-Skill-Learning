from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from skillopt.config import flatten_config, load_config

from skillopt_verusage.cost_ledger import write_cost_ledger
from skillopt_verusage.train import _adapter, _expand


def _balanced_items(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    groups = {
        task_type: [item for item in items if item["task_type"] == task_type]
        for task_type in ("anvil", "ironkv")
    }
    first_count = count // 2
    selected = groups["anvil"][:first_count] + groups["ironkv"][: count - first_count]
    if len(selected) != count:
        raise ValueError(f"cannot select {count} balanced calibration tasks")
    return selected


def _response_audit(root: Path, results: list[dict[str, Any]]) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    for path in sorted(root.rglob("target_calls.jsonl")):
        calls.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    accepted = [call for call in calls if call.get("accepted") is True]
    silent = [
        call
        for call in accepted
        if "length" in (call.get("finish_reasons") or [])
        or not any(str(text).strip() for text in call.get("responses") or [])
    ]
    unresolved = [
        result
        for result in results
        if any(
            marker in str(result.get("fail_reason") or "")
            for marker in (
                "DeepSeek request failed",
                "REQUEST_BUDGET_EXCEEDED",
                "DEEPSEEK_BUDGET_APPROVAL_REQUIRED",
            )
        )
    ]
    explicit_issues = [call for call in calls if call.get("response_issue")]
    return {
        "requests": len(calls),
        "accepted_requests": len(accepted),
        "explicitly_rejected_requests": len(explicit_issues),
        "silent_truncations": len(silent),
        "unresolved_response_failures": len(unresolved),
        "task_ledgers": len(list(root.rglob("target_calls.jsonl"))),
        "passed": not silent and not unresolved,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--task-count", type=int, default=8)
    parser.add_argument("--task-ids", nargs="+")
    args = parser.parse_args()
    structured = _expand(load_config(str(args.config), []))
    cfg = flatten_config(structured)
    adapter = _adapter(cfg)
    adapter.setup(cfg)
    root = Path(cfg["out_root"]).resolve()
    if args.task_ids:
        by_id = {item["id"]: item for item in adapter.dataloader.train_items}
        missing = [item_id for item_id in args.task_ids if item_id not in by_id]
        if missing:
            raise ValueError(f"unknown training task ids: {missing}")
        items = [by_id[item_id] for item_id in args.task_ids]
    else:
        items = _balanced_items(adapter.dataloader.train_items, args.task_count)
    skill_path = Path(cfg["skill_init"])
    skill_text = skill_path.read_text(encoding="utf-8")
    results = adapter.rollout(items, skill_text, str(root))
    audit = _response_audit(root, results)
    summary = {
        "schema_version": "1",
        "status": "complete",
        "kind": "deepseek_target_calibration",
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "skill_sha256": hashlib.sha256(skill_text.encode("utf-8")).hexdigest(),
        "task_ids": [item["id"] for item in items],
        "task_types": [item["task_type"] for item in items],
        "strict_solved": sum(int(result["hard"]) for result in results),
        "response_audit": audit,
        "results": results,
    }
    (root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary["cost_ledger"] = write_cost_ledger(root)
    (root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

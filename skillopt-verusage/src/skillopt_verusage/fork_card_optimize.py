from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "gpt-5.6-sol"
MAX_CANDIDATE_BYTES = 4_000


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _require_run_child(path: Path) -> Path:
    configured = os.environ.get("VERUS_SKILL_RUN_ROOT")
    if not configured:
        raise RuntimeError("VERUS_SKILL_RUN_ROOT is not set")
    root = Path(configured).resolve(); resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"path must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    return resolved


def prepare_reflection_inputs(packet_root: Path, out_dir: Path) -> tuple[list[dict[str, Any]], Path]:
    packet_root = _require_run_child(packet_root)
    out_dir = _require_run_child(out_dir)
    if packet_root not in out_dir.parents:
        raise ValueError("optimizer output must be inside the packet root")
    manifest = json.loads((packet_root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "skillopt-fork-packet-v1":
        raise ValueError("unsupported fork packet schema")
    if manifest.get("optimizer_view") != "hint_visible":
        raise ValueError("first diagnostic requires the hint-visible packet view")
    tasks = manifest.get("tasks") or []
    if not tasks:
        raise ValueError("fork packet contains no tasks")
    predictions = out_dir / "reflection_inputs"
    results: list[dict[str, Any]] = []
    for task in tasks:
        project = str(task["project"]).lower()
        synthetic_id = f"fork_{project}"
        index = (packet_root / str(task["optimizer_index"])).resolve()
        if packet_root not in index.parents or not index.is_file():
            raise ValueError(f"optimizer index escapes packet root: {index}")
        relative_index = os.path.relpath(index, packet_root)
        conversation = [{
            "role": "system",
            "content": (
                "This is one task-grouped fork packet, not an ordinary linear "
                "trajectory. Read every file required by the packet index before "
                f"proposing a card: `{relative_index}`. Treat all checkpoint "
                "branches as correlated observations with total task weight one."
            ),
        }]
        task_dir = predictions / synthetic_id
        _write_json(task_dir / "conversation.json", conversation)
        (task_dir / "target_user_prompt.txt").write_text(
            "Generate reusable stage-triggered Verus skill cards from the fork evidence.\n",
            encoding="utf-8",
        )
        results.append({
            "id": synthetic_id,
            "hard": 0,
            "task_description": f"Task-grouped {str(task['project']).upper()} fork evidence",
            "task_type": "verus_fork_packet",
            "fail_reason": "Diagnostic reflection over original, hint, and matched no-hint branches",
            "n_turns": int(task["checkpoint_count"]),
            "task_weight": 1,
            "source_task_id_hash": hashlib.sha256(str(task["task_id"]).encode()).hexdigest(),
            "optimizer_index": relative_index,
        })
    _write_json(out_dir / "reflection_results.json", results)
    return results, predictions


def _card_audit(candidate: str, ranked: dict[str, Any], apply_report: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(candidate.encode()) > MAX_CANDIDATE_BYTES:
        errors.append(f"candidate exceeds {MAX_CANDIDATE_BYTES} bytes")
    if re.search(r"\b[0-9a-f]{20}\b", candidate, flags=re.IGNORECASE):
        errors.append("candidate contains a task-like identifier")
    if any(not str(row.get("status", "")).startswith("applied") for row in apply_report):
        errors.append("one or more selected edits were not applied")
    content = "\n".join(
        str(edit.get("content", ""))
        for edit in ranked.get("edits", [])
        if isinstance(edit, dict)
    )
    for label in ("Trigger:", "Action:", "Validate:", "Avoid when:"):
        if label not in content:
            errors.append(f"selected cards omit {label}")
    for forbidden in ("```", "/zp_vegeta/", "assert(", "assume(", "admit("):
        if forbidden in content:
            errors.append(f"selected cards contain forbidden concrete content: {forbidden}")
    return errors


def optimize(
    packet_root: Path,
    out_dir: Path,
    seed_skill: Path,
    *,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = "high",
    analyst_workers: int = 3,
    codex_path: str = "codex",
) -> dict[str, Any]:
    packet_root = _require_run_child(packet_root); out_dir = _require_run_child(out_dir)
    if packet_root not in out_dir.parents:
        raise ValueError("optimizer output must be inside the packet root")
    out_dir.mkdir(parents=True, exist_ok=True)
    results, predictions = prepare_reflection_inputs(packet_root, out_dir)
    current_skill = seed_skill.resolve().read_text(encoding="utf-8")
    repo = Path(__file__).resolve().parents[3]
    analyst_prompt = (repo / "skillopt-verusage/prompts/fork_cards/analyst.md").read_text(encoding="utf-8")
    invocation = {
        "schema_version": "fork-card-skillopt-v1",
        "packet_manifest_sha256": _sha256(packet_root / "manifest.json"),
        "seed_skill_sha256": _sha256(seed_skill.resolve()),
        "optimizer_model": model,
        "reasoning_effort": reasoning_effort,
        "task_count": len(results),
        "minibatch_size": 1,
        "per_task_edit_budget": 2,
        "global_edit_budget": 4,
        "analyst_prompt_sha256": hashlib.sha256(analyst_prompt.encode()).hexdigest(),
        "diagnostic_only": True,
    }
    manifest_path = out_dir / "optimizer_manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != invocation:
        raise ValueError("existing optimizer invocation differs")
    _write_json(manifest_path, invocation)

    from skillopt.engine.trainer import _normalise_patches
    from skillopt.gradient.aggregate import merge_patches
    from skillopt.gradient.reflect import run_minibatch_reflect
    from skillopt.model import configure_codex_exec, reset_token_tracker, set_optimizer_backend, set_optimizer_deployment, set_reasoning_effort
    from skillopt.optimizer.clip import rank_and_select
    from skillopt.optimizer.skill import apply_patch_with_report
    from skillopt_verusage.codex_reoptimize import _install_prompt_free_codex_ledger, _ledger_summary

    set_optimizer_backend("codex_exec"); set_optimizer_deployment(model); set_reasoning_effort(reasoning_effort)
    configure_codex_exec(path=codex_path,sandbox="read-only",profile="",full_auto=False,reasoning_effort=reasoning_effort,use_sdk="false",network_access=False,web_search=False,approval_policy="never")
    os.environ["CODEX_WORKING_DIRECTORY"] = str(packet_root)
    os.environ["SKILLOPT_PATH_REFERENCES"] = "1"
    ledger = out_dir / "optimizer_calls.jsonl"; _install_prompt_free_codex_ledger(ledger); reset_token_tracker()

    raw = run_minibatch_reflect(results,current_skill,str(predictions),str(out_dir/'patches'),workers=analyst_workers,failure_only=True,minibatch_size=1,edit_budget=2,random_seed=None,error_system=analyst_prompt,success_system=None,step_buffer_context="",meta_skill_context="",update_mode="patch",skill_aware_reflection=False)
    failure, success = _normalise_patches(raw, "patch")
    if len(failure) != len(results) or success:
        raise RuntimeError(f"expected one failure patch per task, got failure={len(failure)} success={len(success)}")
    merged = merge_patches(current_skill,failure,[],batch_size=8,verbose=True,workers=analyst_workers,update_mode="patch",meta_skill_context="")
    _write_json(out_dir / "merged_patch.json", merged)
    ranked = rank_and_select(current_skill,merged,max_edits=4,update_mode="patch",meta_skill_context="")
    _write_json(out_dir / "ranked_edits.json", ranked)
    candidate, apply_report = apply_patch_with_report(current_skill, ranked)
    (out_dir / "candidate_skill.md").write_text(candidate, encoding="utf-8")
    _write_json(out_dir / "edit_apply_report.json", apply_report)
    errors = _card_audit(candidate, ranked, apply_report)
    result = {
        "status": "candidate_pending_manual_audit" if not errors else "rejected_by_automatic_audit",
        "diagnostic_only": True,
        "task_count": len(results),
        "task_weight_total": len(results),
        "checkpoint_branches_are_not_optimizer_samples": True,
        "raw_task_patches": len(raw),
        "merged_edits": len(merged.get("edits", [])),
        "selected_edits": len(ranked.get("edits", [])),
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "candidate_bytes": len(candidate.encode()),
        "audit_errors": errors,
        "codex_usage": _ledger_summary(ledger),
    }
    _write_json(out_dir / "optimizer_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed-skill", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--analyst-workers", type=int, default=3)
    parser.add_argument("--codex-path", default=os.environ.get("CODEX_CLI_BIN", "codex"))
    args = parser.parse_args()
    print(json.dumps(optimize(args.packet_root,args.out_dir,args.seed_skill,model=args.model,reasoning_effort=args.reasoning_effort,analyst_workers=args.analyst_workers,codex_path=args.codex_path),ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()

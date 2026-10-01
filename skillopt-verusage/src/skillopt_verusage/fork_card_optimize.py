from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
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
    if manifest.get("optimizer_view") not in {"hint_visible", "original_only"}:
        raise ValueError("unsupported optimizer evidence view")
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
                "This is one source-task evidence packet. Its index defines the "
                "available original or augmented traces. Read that index before "
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


def _card_audit(candidate: str, ranked: dict[str, Any], apply_report: list[dict[str, Any]], *, bank: bool = False) -> list[str]:
    errors: list[str] = []
    if not bank and len(candidate.encode()) > MAX_CANDIDATE_BYTES:
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
    edits = ranked.get("edits", [])
    if not edits:
        errors.append("no cards selected")
    for index, edit in enumerate(edits):
        if edit.get("op") != "append":
            errors.append(f"card {index} is not an append edit")
        for label in ("Trigger:", "Action:", "Validate:", "Avoid when:") + (("Why:",) if bank else ()):
            if label not in str(edit.get("content", "")):
                errors.append(f"card {index} omits {label}")
        if bank and len(str(edit.get("content", "")).encode()) > 1200:
            errors.append(f"card {index} exceeds 1200 bytes")
    for forbidden in ("```", "/zp_vegeta/", "assert(", "assume(", "admit("):
        if forbidden in content:
            errors.append(f"selected cards contain forbidden concrete content: {forbidden}")
    return errors


def attach_card_evidence(proposal: dict[str, Any], task_id: str) -> None:
    """Keep the full sidecar inside the patch consumed by native SkillOpt merge."""
    evidence = proposal.get("card_evidence")
    edits = proposal["patch"]["edits"]
    if not isinstance(evidence, list) or sorted(e.get("card_index", -1) for e in evidence) != list(range(len(edits))):
        raise ValueError(f"incomplete card evidence for {task_id}")
    proposal["patch"]["card_evidence"] = [
        {**e, "source_card": f"{task_id}:{e['card_index']}"} for e in evidence
    ]
    for index, edit in enumerate(edits):
        edit["source_cards"] = [f"{task_id}:{index}"]


def audit_bank_provenance(merged: dict[str, Any], patches: list[dict[str, Any]]) -> list[str]:
    expected = {e["source_card"] for p in patches for e in p["card_evidence"]}
    observed = []
    errors = []
    for edit in merged.get("edits", []):
        refs = edit.get("source_cards", [])
        if not refs or any(ref not in expected for ref in refs):
            errors.append("card has missing or unknown source references")
        observed.extend(refs)
        support = len({ref.split(":")[0] for ref in refs})
        if edit.get("support_count") != support:
            errors.append("support count differs from distinct source tasks")
    for row in merged.get("dropped_cards", []):
        if not row.get("reason"):
            errors.append("dropped card lacks a reason")
        observed.append(row.get("source_card"))
    if set(observed) != expected or len(observed) != len(set(observed)):
        errors.append("each source card must be retained/merged/dropped exactly once")
    reviews = [row.get("source_card") for row in merged.get("evidence_review", [])]
    if set(reviews) != expected or len(reviews) != len(set(reviews)):
        errors.append("each source card needs exactly one evidence review")
    return errors


def select_contrast_pair(rows: list[dict[str, Any]]) -> list[str]:
    """Nominate one cheap successful hint and one adverse example per task."""
    candidates = []
    for row in rows:
        arms = row["arms"]
        if not arms["no_hint"]["dual_pass"]:
            continue
        baseline = arms["no_hint"]["actor_completion_tokens"]
        for arm in ("v1", "v2"):
            value = arms[arm]
            candidates.append((row["checkpoint"], bool(value["dual_pass"]),
                               1 - value["actor_completion_tokens"] / baseline))
    successes = [row for row in candidates if row[1]]
    if not successes:
        raise ValueError("no successful hint/no-hint contrast")
    best = max(successes, key=lambda row: row[2])[0]
    others = [row for row in candidates if row[0] != best]
    if not others:
        raise ValueError("contrast selection requires two distinct checkpoints")
    adverse = min(others, key=lambda row: (row[1], row[2]))[0]
    return [best, adverse]


def add_efficiency_views(packet_root: Path, out_dir: Path, results: list[dict[str, Any]],
                         predictions: Path, costs_path: Path, mode: str) -> dict[str, list[str]]:
    costs = json.loads(costs_path.read_text())
    focus_by_task = {}
    for result in results:
        project = result["id"].removeprefix("fork_")
        rows = [row for row in costs["rows"] if row["project"].lower() == project]
        if len(rows) != result["n_turns"]:
            raise ValueError(f"cost coverage mismatch for {project}")
        for row in rows:
            for arm, cost in row["arms"].items():
                run = packet_root / "tasks" / project / "checkpoints" / row["checkpoint"] / "branches" / arm / "trace/result.json"
                actual = json.loads(run.read_text())
                if cost["actor_completion_tokens"] != actual["usage"]["completion_tokens"] or cost["dual_pass"] != bool(actual["hard"]):
                    raise ValueError(f"cost/validation mismatch: {run}")
        focus = select_contrast_pair(rows)
        focus_by_task[project] = focus
        scope = (
            "Read all checkpoint forks before proposing two cards for this task."
            if mode == "efficiency_task" else
            "Analyze each nominated checkpoint locally before generalizing. Read both "
            "nominated forks completely, including every arm and original prefix/suffix. "
            "Use the other checkpoints for counterexamples only if needed. Still propose "
            "at most two cards for the entire source task; do not weight checkpoints as tasks."
        )
        view = out_dir / "cost_views" / f"{project}.json"
        _write_json(view, {"project": project, "reading_scope": scope,
                          "nominated_checkpoints": focus if mode == "efficiency_focus" else [],
                          "selection_policy": "best successful relative reduction and worst distinct adverse checkpoint; descriptive train-only selection",
                          "metric": costs["metric"], "caveat": costs["caveat"], "rows": rows})
        conv = predictions / result["id"] / "conversation.json"
        _write_json(conv, [{"role": "system", "content": (
            f"This is source task {project.upper()}, total weight one. Read cost view "
            f"`{view.relative_to(packet_root)}` first. {scope} Complete evidence index: "
            f"`{result['optimizer_index']}`. Evidence paths beginning checkpoints/ or "
            f"common/ are relative to tasks/{project}/. Preserve this task identity in "
            "your evidence. Do not read any other optimizer output or report."
        )}])
    return focus_by_task


def optimize(
    packet_root: Path,
    out_dir: Path,
    seed_skill: Path,
    *,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = "high",
    analyst_workers: int = 3,
    codex_path: str = "codex",
    reuse_reflections_from: Path | None = None,
    analysis_mode: str = "standard",
    paired_costs: Path | None = None,
    capture_events: bool = False,
    merge_profile: str = "legacy",
) -> dict[str, Any]:
    packet_root = _require_run_child(packet_root); out_dir = _require_run_child(out_dir)
    if packet_root not in out_dir.parents:
        raise ValueError("optimizer output must be inside the packet root")
    out_dir.mkdir(parents=True, exist_ok=True)
    results, predictions = prepare_reflection_inputs(packet_root, out_dir)
    current_skill = seed_skill.resolve().read_text(encoding="utf-8")
    repo = Path(__file__).resolve().parents[3]
    prompt_name = {"standard": "analyst.md", "matched_evidence": "matched_analyst.md"}.get(analysis_mode, "efficiency_analyst.md")
    analyst_prompt = (repo / "skillopt-verusage/prompts/fork_cards" / prompt_name).read_text(encoding="utf-8")
    if merge_profile not in {"legacy", "evidence_bank"}:
        raise ValueError("unsupported merge profile")
    bank = merge_profile == "evidence_bank"
    merge_prompt = (repo / "skillopt-verusage/prompts/fork_cards" / ("merge_evidence_bank.md" if bank else "merge.md")).read_text(encoding="utf-8")
    invocation = {
        "schema_version": "fork-card-skillopt-v1",
        "packet_manifest_sha256": _sha256(packet_root / "manifest.json"),
        "seed_skill_sha256": _sha256(seed_skill.resolve()),
        "optimizer_model": model,
        "reasoning_effort": reasoning_effort,
        "task_count": len(results),
        "minibatch_size": 1,
        "per_task_edit_budget": 2,
        "global_edit_budget": None if bank else 4,
        "merge_profile": merge_profile,
        "evidence_sidecars_forwarded": bank,
        "analyst_prompt_sha256": hashlib.sha256(analyst_prompt.encode()).hexdigest(),
        "merge_prompt_sha256": hashlib.sha256(merge_prompt.encode()).hexdigest(),
        "diagnostic_only": True,
        "analysis_mode": analysis_mode,
    }
    if analysis_mode in {"efficiency_task", "efficiency_focus"}:
        if paired_costs is None:
            raise ValueError("efficiency analysis requires paired costs")
        invocation["paired_costs_sha256"] = _sha256(paired_costs)
        invocation["nominated_checkpoints"] = add_efficiency_views(packet_root,out_dir,results,predictions,paired_costs,analysis_mode)
    reused_patches = []
    if reuse_reflections_from is not None:
        source = _require_run_child(reuse_reflections_from)
        if source == out_dir or packet_root not in source.parents:
            raise ValueError("reused reflections must come from another run in this packet")
        source_manifest = json.loads((source / "optimizer_manifest.json").read_text())
        if source_manifest.get("analysis_mode", "standard") != analysis_mode:
            raise ValueError("reused reflection analysis mode differs")
        for key in ("packet_manifest_sha256", "seed_skill_sha256", "optimizer_model", "reasoning_effort", "analyst_prompt_sha256", "task_count", "minibatch_size", "per_task_edit_budget"):
            if source_manifest.get(key) != invocation[key]:
                raise ValueError(f"reused reflection contract differs: {key}")
        if source_manifest.get("paired_costs_sha256") != invocation.get("paired_costs_sha256"):
            raise ValueError("reused reflection paired costs differ")
        reused_patches = sorted((source / "patches").glob("minibatch_fail_*.json"))
        if len(reused_patches) != len(results):
            raise ValueError("reused reflection set is incomplete")
        invocation["reused_reflections"] = {
            "source": str(source.relative_to(packet_root)),
            "patch_sha256": {p.name: _sha256(p) for p in reused_patches},
        }
    manifest_path = out_dir / "optimizer_manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != invocation:
        raise ValueError("existing optimizer invocation differs")
    _write_json(manifest_path, invocation)

    from skillopt.engine.trainer import _normalise_patches
    from skillopt.gradient.aggregate import _hierarchical_merge
    from skillopt.gradient.reflect import run_minibatch_reflect
    from skillopt.model import configure_codex_exec, reset_token_tracker, set_optimizer_backend, set_optimizer_deployment, set_reasoning_effort
    from skillopt.optimizer.clip import rank_and_select
    from skillopt.optimizer.skill import apply_patch_with_report
    from skillopt_verusage.codex_reoptimize import _install_prompt_free_codex_ledger, _ledger_summary

    set_optimizer_backend("codex_exec"); set_optimizer_deployment(model); set_reasoning_effort(reasoning_effort)
    if capture_events:
        os.environ["SKILLOPT_REAL_CODEX_BIN"] = shutil.which(codex_path) or codex_path
        os.environ["SKILLOPT_CODEX_TRACE_DIR"] = str(out_dir / "codex_events")
        codex_path = str(repo / "skillopt-verusage/scripts/capture_optimizer_codex.py")
    configure_codex_exec(path=codex_path,sandbox="read-only",profile="",full_auto=False,reasoning_effort=reasoning_effort,use_sdk="false",network_access=False,web_search=False,approval_policy="never")
    os.environ["CODEX_WORKING_DIRECTORY"] = str(packet_root)
    os.environ["SKILLOPT_PATH_REFERENCES"] = "1"
    ledger = out_dir / "optimizer_calls.jsonl"; _install_prompt_free_codex_ledger(ledger); reset_token_tracker()

    if reused_patches:
        (out_dir / "patches").mkdir(exist_ok=True)
        raw = []
        for path in reused_patches:
            shutil.copyfile(path, out_dir / "patches" / path.name)
            raw.append(json.loads(path.read_text()))
    else:
        raw = run_minibatch_reflect(results,current_skill,str(predictions),str(out_dir/'patches'),workers=analyst_workers,failure_only=True,minibatch_size=1,edit_budget=2,random_seed=None,error_system=analyst_prompt,success_system=None,step_buffer_context="",meta_skill_context="",update_mode="patch",skill_aware_reflection=False)
    # Native reflection uses stable filenames but returns asynchronous completion
    # order. Re-read by batch index to bind every proposal to its source task.
    raw = []
    for index, result in enumerate(results):
        path = out_dir / "patches" / f"minibatch_fail_{index:03d}.json"
        proposal = json.loads(path.read_text())
        proposal["patch"]["source_task"] = result["id"]
        proposal["patch"]["evidence_root"] = str(Path(result["optimizer_index"]).parent)
        if bank:
            attach_card_evidence(proposal, result["id"])
        raw.append(proposal)
    failure, success = _normalise_patches(raw, "patch")
    if len(failure) != len(results) or success:
        raise RuntimeError(f"expected one failure patch per task, got failure={len(failure)} success={len(success)}")
    _write_json(out_dir / "merge_inputs.json", failure)
    # Keep all source evidence in one call for this small diagnostic bank.
    # Larger recursive merges need a separate sidecar-retention contract.
    if bank and len(failure) > 8:
        raise ValueError("evidence-bank diagnostic supports at most eight source tasks")
    # Same pinned SkillOpt failure-merge algorithm, with an explicit card
    # contract instead of the general prose-edit system prompt.
    merged = _hierarchical_merge(current_skill,failure,merge_prompt,"patch",batch_size=8,verbose=True,label="fork cards",workers=analyst_workers)
    _write_json(out_dir / "merged_patch.json", merged)
    ranked = merged if bank else rank_and_select(current_skill,merged,max_edits=4,update_mode="patch",meta_skill_context="")
    _write_json(out_dir / "ranked_edits.json", ranked)
    candidate, apply_report = apply_patch_with_report(current_skill, ranked)
    (out_dir / "candidate_skill.md").write_text(candidate, encoding="utf-8")
    _write_json(out_dir / "edit_apply_report.json", apply_report)
    errors = _card_audit(candidate, ranked, apply_report, bank=bank)
    if bank:
        errors.extend(audit_bank_provenance(merged, failure))
        _write_json(out_dir / "card_bank.json", {
            "schema_version": "stage-card-bank-v1",
            "cards": [{"id": f"card-{i+1:03d}", "content": edit["content"]}
                      for i, edit in enumerate(ranked.get("edits", []))],
        })
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
    parser.add_argument("--reuse-reflections-from", type=Path)
    parser.add_argument("--analysis-mode", choices=("standard", "efficiency_task", "efficiency_focus", "matched_evidence"), default="standard")
    parser.add_argument("--paired-costs", type=Path)
    parser.add_argument("--capture-events", action="store_true")
    parser.add_argument("--merge-profile", choices=("legacy", "evidence_bank"), default="legacy")
    args = parser.parse_args()
    print(json.dumps(optimize(args.packet_root,args.out_dir,args.seed_skill,model=args.model,reasoning_effort=args.reasoning_effort,analyst_workers=args.analyst_workers,codex_path=args.codex_path,reuse_reflections_from=args.reuse_reflections_from,analysis_mode=args.analysis_mode,paired_costs=args.paired_costs,capture_events=args.capture_events,merge_profile=args.merge_profile),ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()

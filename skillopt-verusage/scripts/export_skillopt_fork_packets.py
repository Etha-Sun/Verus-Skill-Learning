#!/usr/bin/env python3
"""Export task-grouped, branch-aware SkillOpt evidence below the run root.

The exporter copies complete recorded conversations/event streams. It also
creates exact original-prefix/original-suffix views at every checkpoint. It
never rewrites a fresh continuation as though its actor saw the prefix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


COMPLETE_TRACE_FILES = (
    "agent_events.jsonl",
    "codex_events.raw.jsonl",
    "conversation.json",
    "result.json",
    "run_manifest.json",
    "prompt.txt",
    "target_user_prompt.txt",
    "workspace/input.rs",
    "workspace/candidate.rs",
)

OPTIONAL_AUDIT_FILES = (
    "validation.json",
    "fidelity_audit.json",
    "workspace_inventory.json",
    "visibility_manifest.json",
    "continuation_contract.json",
    "condition_contract.json",
    "hint_contract.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def require_output_root(path: Path) -> Path:
    configured = os.environ.get("VERUS_SKILL_RUN_ROOT")
    if not configured:
        raise RuntimeError("VERUS_SKILL_RUN_ROOT is not set")
    run_root = Path(configured).resolve()
    output = path.resolve()
    if output == run_root or run_root not in output.parents:
        raise ValueError(f"output must be a child of VERUS_SKILL_RUN_ROOT: {output}")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    return output


def copy_complete_trace(source: Path, destination: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    snapshots = source / "snapshots"
    if not snapshots.is_dir():
        raise FileNotFoundError(f"incomplete recorded trajectory: {snapshots}")
    snapshot_files = sorted(path for path in snapshots.rglob("*") if path.is_file())
    if not snapshot_files:
        raise FileNotFoundError(f"empty recorded snapshot directory: {snapshots}")
    relative_files = [
        *COMPLETE_TRACE_FILES,
        *(str(path.relative_to(source)) for path in snapshot_files),
        *(relative for relative in OPTIONAL_AUDIT_FILES if (source / relative).is_file()),
    ]
    for relative in relative_files:
        src = source / relative
        if not src.is_file():
            raise FileNotFoundError(f"incomplete recorded trajectory: {src}")
        dst = destination / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        if sha256(src) != sha256(dst):
            raise RuntimeError(f"copy hash mismatch: {src}")
        hashes[relative] = sha256(dst)
    for event in load_jsonl(source / "agent_events.jsonl"):
        data = event.get("data") or {}
        for key in ("snapshot", "diff"):
            relative = data.get(key)
            if relative is None:
                continue
            if not isinstance(relative, str) or relative not in hashes or not relative.startswith("snapshots/"):
                raise ValueError(f"unresolved {key} reference in {source}")
            if key == "snapshot" and event.get("candidate_sha256") != hashes[relative]:
                raise ValueError(f"snapshot candidate hash mismatch in {source}: {relative}")
    return hashes


def checkpoint_rows(selection: dict[str, Any]) -> list[tuple[int, int, str]]:
    rows = []
    for row in selection["checkpoints"]:
        ordinal = int(row["ordinal"])
        event_index = row.get("event_index")
        if not isinstance(event_index, int):
            raise ValueError(f"checkpoint CP{ordinal:02d} lacks an original event index")
        rows.append((ordinal, event_index, str(row["checkpoint_sha256"])))
    if len({ordinal for ordinal, _, _ in rows}) != len(rows):
        raise ValueError("duplicate checkpoint ordinal")
    return rows


def selection_for(root: Path, task_id: str) -> dict[str, Any]:
    selection = load_json(root / "selection.json")
    if selection["task"]["id"] != task_id:
        raise ValueError(f"selection task mismatch: {root}")
    return selection


def source_checkpoint(root: Path, task_id: str, ordinal: int, arm: str) -> Path:
    if arm == "no_hint":
        return root / "checkpoints" / task_id / f"CP{ordinal:02d}.rs"
    return root / "hint-private" / task_id / f"CP{ordinal:02d}" / "checkpoint.rs"


def branch_run(root: Path, task_id: str, ordinal: int) -> Path:
    return root / "runs" / task_id / f"CP{ordinal:02d}"


def copy_branch(
    root: Path,
    destination: Path,
    task_id: str,
    ordinal: int,
    arm: str,
    checkpoint_sha: str,
) -> dict[str, Any]:
    checkpoint = source_checkpoint(root, task_id, ordinal, arm)
    if not checkpoint.is_file() or sha256(checkpoint) != checkpoint_sha:
        raise ValueError(f"{arm} CP{ordinal:02d} checkpoint hash mismatch")
    checkpoint_dest = destination / "checkpoint.rs"
    checkpoint_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(checkpoint, checkpoint_dest)
    hashes = copy_complete_trace(branch_run(root, task_id, ordinal), destination / "trace")
    branch: dict[str, Any] = {
        "arm": arm,
        "fresh_actor_session": True,
        "historical_prefix_visible_to_actor": False,
        "teacher_hint_visible_to_actor": arm in {"v1", "v2"},
        "checkpoint_sha256": checkpoint_sha,
        "checkpoint_file": "checkpoint.rs",
        "trace_root": "trace",
        "complete_trace_sha256": hashes,
    }
    if arm in {"v1", "v2"}:
        private = root / "hint-private" / task_id / f"CP{ordinal:02d}"
        hint_source = private / "hint.json"
        if not hint_source.is_file():
            raise FileNotFoundError(f"missing {arm} hint: {hint_source}")
        hint = load_json(hint_source)
        if hint.get("checkpoint_sha256") != checkpoint_sha:
            raise ValueError(f"{arm} CP{ordinal:02d} hint checkpoint mismatch")
        shutil.copyfile(hint_source, destination / "teacher_hint.json")
        (destination / "teacher_hint.txt").write_text(
            str(hint["hint_text"]), encoding="utf-8"
        )
        branch["teacher_hint_file"] = "teacher_hint.txt"
        branch["teacher_hint_sha256"] = sha256(destination / "teacher_hint.txt")
        branch["teacher_hint_label"] = "teacher intervention; not verifier evidence"
        replay_source = private / "published_hint_replay.json"
        if replay_source.is_file():
            replay = load_json(replay_source)
            if replay.get("hint_generation_api_called") is not False:
                raise ValueError(f"invalid published hint replay provenance CP{ordinal:02d}")
            if replay.get("checkpoint_sha256") != checkpoint_sha:
                raise ValueError(f"published hint replay checkpoint mismatch CP{ordinal:02d}")
            shutil.copyfile(replay_source, destination / "published_hint_replay.json")
            branch["hint_source"] = "reviewed published intervention replay"
            branch["hint_generation_api_called_in_current_run"] = False
    else:
        contract = load_json(branch_run(root, task_id, ordinal) / "condition_contract.json")
        if contract.get("condition") != "matched_no_hint":
            raise ValueError(f"invalid no-hint condition contract CP{ordinal:02d}")
        if contract.get("teacher_hint_visible_to_actor") is not False:
            raise ValueError(f"no-hint visibility mismatch CP{ordinal:02d}")
        write_json(destination / "condition_contract.json", contract)
    write_json(destination / "branch.json", branch)
    return branch


def render_task_index(task: dict[str, Any]) -> str:
    lines = [
        f"# Fork evidence: {task['project']} / {task['task_id']}",
        "",
        "Read the complete original trace and every listed branch before proposing cards.",
        "A fresh continuation did not observe the historical prefix. Teacher hints are",
        "labeled interventions and are not verifier evidence.",
        "",
        "For each proposed card provide: title; observable trigger/stage; recommended",
        "action; validation check; failure boundary; supporting and contradicting branches.",
        "Avoid task identifiers and task-specific function names in the deployable card.",
        "",
        "Original complete trace: `common/original/`",
        "",
    ]
    for checkpoint in task["checkpoints"]:
        name = checkpoint["checkpoint_id"]
        lines.extend(
            [
                f"## {name}",
                "",
                f"Original event index: {checkpoint['original_event_index']}",
                f"Checkpoint source: `checkpoints/{name}/checkpoint.rs`",
                f"Original prefix: `checkpoints/{name}/original_prefix.agent_events.jsonl`",
                f"Original suffix: `checkpoints/{name}/original_suffix.agent_events.jsonl`",
                f"Original verifier diagnostic: `checkpoints/{name}/original_diagnostic.txt`",
                f"v1 fresh continuation: `checkpoints/{name}/branches/v1/trace/`",
                f"v1 teacher intervention: `checkpoints/{name}/branches/v1/teacher_hint.txt`",
                f"v2 fresh continuation: `checkpoints/{name}/branches/v2/trace/`",
                f"v2 teacher intervention: `checkpoints/{name}/branches/v2/teacher_hint.txt`",
                f"matched no-hint continuation: `checkpoints/{name}/branches/no_hint/trace/`",
                "",
            ]
        )
    return "\n".join(lines)


def export_task(spec: dict[str, Any], output: Path) -> dict[str, Any]:
    task_id = str(spec["task_id"]); project = str(spec["project"])
    original = Path(spec["original_run"]).resolve()
    roots = {name: Path(spec["arms"][name]).resolve() for name in ("v1", "v2", "no_hint")}
    selections = {name: selection_for(root, task_id) for name, root in roots.items()}
    canonical = checkpoint_rows(selections["v1"])
    for name in ("v2", "no_hint"):
        if checkpoint_rows(selections[name]) != canonical:
            raise ValueError(f"{project} {name} checkpoint selection differs from v1")

    task_dir = output / "tasks" / project.lower()
    original_hashes = copy_complete_trace(original, task_dir / "common" / "original")
    original_events = load_jsonl(original / "agent_events.jsonl")
    by_index = {row.get("event_index"): row for row in original_events}
    if len(by_index) != len(original_events):
        raise ValueError(f"duplicate or absent original event indexes: {task_id}")
    task_manifest: dict[str, Any] = {
        "schema_version": "skillopt-fork-task-v1",
        "project": project,
        "task_id": task_id,
        "task": selections["v1"]["task"],
        "task_weight": 1,
        "branch_samples_are_not_independent_tasks": True,
        "original_complete_trace_sha256": original_hashes,
        "checkpoints": [],
    }
    for ordinal, event_index, checkpoint_sha in canonical:
        cp_name = f"CP{ordinal:02d}"; cp_dir = task_dir / "checkpoints" / cp_name
        event = by_index.get(event_index)
        if not event or event.get("actor") != "verus" or event.get("type") != "verifier":
            raise ValueError(f"{project} {cp_name} is not an original Verus event")
        if event.get("candidate_sha256") != checkpoint_sha:
            raise ValueError(f"{project} {cp_name} original event hash mismatch")
        checkpoint = source_checkpoint(roots["v1"], task_id, ordinal, "v1")
        cp_dir.mkdir(parents=True, exist_ok=True); shutil.copyfile(checkpoint, cp_dir / "checkpoint.rs")
        prefix = [row for row in original_events if int(row["event_index"]) <= event_index]
        suffix = [row for row in original_events if int(row["event_index"]) > event_index]
        if prefix + suffix != original_events:
            raise RuntimeError(f"{project} {cp_name} prefix/suffix reconstruction failed")
        write_jsonl(cp_dir / "original_prefix.agent_events.jsonl", prefix)
        write_jsonl(cp_dir / "original_suffix.agent_events.jsonl", suffix)
        raw = event.get("data", {}).get("raw_codex_event", {}).get("item", {})
        (cp_dir / "original_diagnostic.txt").write_text(
            str(raw.get("aggregated_output") or ""), encoding="utf-8"
        )
        branches = {
            arm: copy_branch(root, cp_dir / "branches" / arm, task_id, ordinal, arm, checkpoint_sha)
            for arm, root in roots.items()
        }
        cp_manifest = {
            "checkpoint_id": cp_name,
            "ordinal": ordinal,
            "original_event_index": event_index,
            "checkpoint_sha256": checkpoint_sha,
            "prefix_event_count": len(prefix),
            "suffix_event_count": len(suffix),
            "prefix_plus_suffix_reconstructs_original": True,
            "branches": branches,
        }
        write_json(cp_dir / "fork.json", cp_manifest)
        task_manifest["checkpoints"].append(cp_manifest)
    write_json(task_dir / "task.json", task_manifest)
    (task_dir / "OPTIMIZER_HINT_VISIBLE.md").write_text(
        render_task_index(task_manifest), encoding="utf-8"
    )
    return task_manifest


def export(config: dict[str, Any]) -> dict[str, Any]:
    output = require_output_root(Path(config["output_root"]))
    tasks = [export_task(spec, output) for spec in config["tasks"]]
    if len({task["task_id"] for task in tasks}) != len(tasks):
        raise ValueError("duplicate task in export config")
    manifest = {
        "schema_version": "skillopt-fork-packet-v1",
        "optimizer_view": "hint_visible",
        "task_count": len(tasks),
        "task_weight_total": sum(int(task["task_weight"]) for task in tasks),
        "branch_count": sum(len(task["checkpoints"]) * 3 for task in tasks),
        "tasks": [
            {
                "project": task["project"],
                "task_id": task["task_id"],
                "task_weight": task["task_weight"],
                "checkpoint_count": len(task["checkpoints"]),
                "optimizer_index": f"tasks/{task['project'].lower()}/OPTIMIZER_HINT_VISIBLE.md",
            }
            for task in tasks
        ],
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(load_json(args.config)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

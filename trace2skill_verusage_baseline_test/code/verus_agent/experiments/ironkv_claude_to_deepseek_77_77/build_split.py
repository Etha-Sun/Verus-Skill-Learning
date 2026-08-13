#!/usr/bin/env python3
"""Build a deterministic, leakage-aware 77/77 IronKV task split.

The script never copies or edits dataset files.  It groups likely sibling tasks
before assigning whole groups to train or held-out, then writes manifests that
keep held-out trajectories and verified solutions out of the evaluation input
list.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import itertools
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import os
from typing import Iterable


DEFAULT_DATASET_DIR = Path(
    os.environ.get("IRONKV_DATASET_DIR", "UNCONFIGURED_IRONKV_DATASET_DIR")
)
DEFAULT_SEED = 20260811
DEFAULT_SOURCE_THRESHOLD = 0.80
DEFAULT_PROOF_DELTA_THRESHOLD = 0.80

VERUS_RUST_KEYWORDS = {
    "Self", "abstract", "as", "assert", "assume", "async", "await",
    "become", "box", "break", "by", "choose", "const", "continue",
    "crate", "decreases", "do", "dyn", "else", "ensures", "enum",
    "exec", "exists", "extern", "false", "final", "fn", "for",
    "forall", "ghost", "hide", "if", "impl", "in", "invariant",
    "invariant_except_break", "let", "loop", "macro", "match", "mod",
    "move", "mut", "nonlinear_arith", "old", "opens", "override", "priv",
    "proof", "pub", "recommends", "ref", "requires", "return", "reveal",
    "self", "spec", "static", "struct", "super", "tracked", "trait", "true",
    "try", "type", "typeof", "unsafe", "unsized", "use", "virtual", "where",
    "while", "yield",
}


@dataclass(frozen=True)
class Task:
    task_id: str
    module: str
    target: str
    canonical_target: str
    source: Path
    trajectory: Path
    verified: Path
    source_sha256: str
    trajectory_sha256: str
    verified_sha256: str
    source_bytes: int
    trajectory_bytes: int
    verified_bytes: int
    source_lines: int
    trajectory_lines: int
    verified_lines: int


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_count(path: Path) -> int:
    data = path.read_bytes()
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def canonical_target(target: str) -> str:
    """Collapse only explicit wrapper/encoding variants, not general suffixes."""
    if target.startswith("retransmit_un_acked_packets"):
        return "retransmit_un_acked_packets_family"
    result = target
    changed = True
    while changed:
        changed = False
        for suffix in ("_auto", "_temp"):
            if result.endswith(suffix):
                result = result[: -len(suffix)]
                changed = True
    if result.endswith("-poly"):
        result = result[: -len("-poly")]
    # Only the observed send_packet pair uses _seq as an encoding variant.
    if result == "send_packet_seq":
        result = "send_packet"
    return result


def discover_tasks(dataset_dir: Path) -> list[Task]:
    logs = sorted(dataset_dir.glob("*.log"))
    if not logs:
        raise ValueError(f"No .log trajectories found under {dataset_dir}")

    tasks: list[Task] = []
    expected_sources: set[Path] = set()
    expected_verified: set[Path] = set()
    for log in logs:
        task_id = log.stem
        source = dataset_dir / f"{task_id}.rs"
        verified = dataset_dir / f"{task_id}_verified.rs"
        missing = [str(path) for path in (source, verified) if not path.is_file()]
        if missing:
            raise ValueError(f"Incomplete task triplet for {task_id}: {missing}")
        expected_sources.add(source)
        expected_verified.add(verified)
        target = task_id.split("__")[-1]
        tasks.append(
            Task(
                task_id=task_id,
                module=task_id.split("__", 1)[0],
                target=target,
                canonical_target=canonical_target(target),
                source=source.resolve(),
                trajectory=log.resolve(),
                verified=verified.resolve(),
                source_sha256=sha256(source),
                trajectory_sha256=sha256(log),
                verified_sha256=sha256(verified),
                source_bytes=source.stat().st_size,
                trajectory_bytes=log.stat().st_size,
                verified_bytes=verified.stat().st_size,
                source_lines=line_count(source),
                trajectory_lines=line_count(log),
                verified_lines=line_count(verified),
            )
        )

    actual_sources = {
        path.resolve()
        for path in dataset_dir.glob("*.rs")
        if not path.name.endswith("_verified.rs")
    }
    actual_verified = {
        path.resolve() for path in dataset_dir.glob("*_verified.rs")
    }
    if actual_sources != expected_sources or actual_verified != expected_verified:
        raise ValueError("Dataset contains unpaired or extra Rust task files")
    return tasks


def normalize_tokens(text: str) -> list[str]:
    text = re.sub(r"//.*?$|/\*.*?\*/", " ", text, flags=re.MULTILINE | re.DOTALL)
    tokens = re.findall(
        r"[A-Za-z_][A-Za-z_0-9]*|\d+|==>|<==>|===|!==|<=|>=|&&&|"
        r"\|\|\||::|->|[^\s]",
        text,
    )
    normalized: list[str] = []
    for token in tokens:
        if token.isdigit():
            normalized.append("NUM")
        elif re.match(r"^[A-Za-z_]", token) and token not in VERUS_RUST_KEYWORDS:
            normalized.append("ID")
        else:
            normalized.append(token)
    return normalized


def shingles(text: str, width: int) -> set[tuple[str, ...]]:
    tokens = normalize_tokens(text)
    return {
        tuple(tokens[index : index + width])
        for index in range(max(0, len(tokens) - width + 1))
    }


def jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def proof_delta(task: Task) -> str:
    before = task.source.read_text(encoding="utf-8", errors="replace").splitlines()
    after = task.verified.read_text(encoding="utf-8", errors="replace").splitlines()
    additions: list[str] = []
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in {"insert", "replace"}:
            additions.extend(after[j1:j2])
    return "\n".join(additions)


def build_groups(
    tasks: list[Task],
    source_threshold: float,
    proof_delta_threshold: float,
) -> tuple[list[list[int]], list[dict[str, object]], dict[tuple[int, int], tuple[float, float]]]:
    source_shingles = {
        index: shingles(task.source.read_text(encoding="utf-8", errors="replace"), 7)
        for index, task in enumerate(tasks)
    }
    delta_shingles = {
        index: shingles(proof_delta(task), 5) for index, task in enumerate(tasks)
    }
    dsu = DisjointSet(len(tasks))
    edges: list[dict[str, object]] = []
    similarities: dict[tuple[int, int], tuple[float, float]] = {}

    for left, right in itertools.combinations(range(len(tasks)), 2):
        source_similarity = jaccard(source_shingles[left], source_shingles[right])
        delta_similarity = jaccard(delta_shingles[left], delta_shingles[right])
        similarities[(left, right)] = (source_similarity, delta_similarity)
        reasons: list[str] = []
        if tasks[left].target == tasks[right].target:
            reasons.append("same_target_name")
        if tasks[left].canonical_target == tasks[right].canonical_target:
            if tasks[left].target != tasks[right].target:
                reasons.append("same_canonical_target_variant")
        if source_similarity >= source_threshold:
            reasons.append("source_structure_similarity")
        if delta_similarity >= proof_delta_threshold:
            reasons.append("proof_delta_structure_similarity")
        if reasons:
            dsu.union(left, right)
            edges.append(
                {
                    "left": tasks[left].task_id,
                    "right": tasks[right].task_id,
                    "reasons": reasons,
                    "source_similarity": round(source_similarity, 6),
                    "proof_delta_similarity": round(delta_similarity, 6),
                }
            )

    by_root: dict[int, list[int]] = defaultdict(list)
    for index in range(len(tasks)):
        by_root[dsu.find(index)].append(index)
    groups = sorted(
        (sorted(indices) for indices in by_root.values()),
        key=lambda indices: (-len(indices), tasks[indices[0]].task_id),
    )
    return groups, edges, similarities


def subset_for_size(
    ordered_groups: list[int], groups: list[list[int]], target_size: int
) -> list[int] | None:
    reachable: dict[int, list[int]] = {0: []}
    for group_index in ordered_groups:
        size = len(groups[group_index])
        additions: dict[int, list[int]] = {}
        for count, selected in list(reachable.items()):
            new_count = count + size
            if new_count <= target_size and new_count not in reachable and new_count not in additions:
                additions[new_count] = selected + [group_index]
        reachable.update(additions)
        if target_size in reachable:
            return reachable[target_size]
    return None


def split_score(train_indices: set[int], tasks: list[Task]) -> tuple[float, tuple[str, ...]]:
    totals = Counter(task.module for task in tasks)
    train = Counter(tasks[index].module for index in train_indices)
    module_score = sum(
        ((train[module] - count / 2.0) / count) ** 2
        for module, count in totals.items()
    )
    missing_penalty = sum(
        1.0
        for module, count in totals.items()
        if count >= 4 and train[module] in {0, count}
    )
    total_log_bytes = sum(task.trajectory_bytes for task in tasks)
    train_log_bytes = sum(tasks[index].trajectory_bytes for index in train_indices)
    byte_score = ((train_log_bytes - total_log_bytes / 2.0) / total_log_bytes) ** 2
    total_log_lines = sum(task.trajectory_lines for task in tasks)
    train_log_lines = sum(tasks[index].trajectory_lines for index in train_indices)
    line_score = ((train_log_lines - total_log_lines / 2.0) / total_log_lines) ** 2
    score = module_score + 4.0 * missing_penalty + byte_score + line_score
    tie_break = tuple(sorted(tasks[index].task_id for index in train_indices))
    return score, tie_break


def choose_split(
    groups: list[list[int]], tasks: list[Task], train_size: int, seed: int
) -> set[int]:
    rng = random.Random(seed)
    group_indices = list(range(len(groups)))
    largest_group = max(group_indices, key=lambda index: len(groups[index]))
    best: tuple[tuple[float, tuple[str, ...]], set[int]] | None = None

    # Deterministic randomized search produces many exact-size component subsets.
    for _ in range(5000):
        order = group_indices[:]
        rng.shuffle(order)
        # Keep the largest repeated family in train, then balance its complement.
        order.remove(largest_group)
        selected_rest = subset_for_size(
            order, groups, train_size - len(groups[largest_group])
        )
        if selected_rest is None:
            continue
        selected_groups = [largest_group, *selected_rest]
        train_indices = {
            task_index
            for group_index in selected_groups
            for task_index in groups[group_index]
        }
        score = split_score(train_indices, tasks)
        if best is None or score < best[0]:
            best = (score, train_indices)

    if best is None:
        raise ValueError(f"Could not construct an exact train split of {train_size}")
    return best[1]


def public_train_record(task: Task, dataset_dir: Path) -> dict[str, object]:
    return {
        "task_id": task.task_id,
        "module": task.module,
        "source_path": str(task.source),
        "trajectory_path": str(task.trajectory),
        "verified_path": str(task.verified),
        "source_relative_path": str(task.source.relative_to(dataset_dir)),
        "trajectory_relative_path": str(task.trajectory.relative_to(dataset_dir)),
        "verified_relative_path": str(task.verified.relative_to(dataset_dir)),
        "source_sha256": task.source_sha256,
        "trajectory_sha256": task.trajectory_sha256,
        "verified_sha256": task.verified_sha256,
        "source_bytes": task.source_bytes,
        "trajectory_bytes": task.trajectory_bytes,
        "verified_bytes": task.verified_bytes,
        "source_lines": task.source_lines,
        "trajectory_lines": task.trajectory_lines,
        "verified_lines": task.verified_lines,
    }


def public_heldout_record(task: Task, dataset_dir: Path) -> dict[str, object]:
    # Deliberately omit trajectory and verified-solution paths and hashes.
    return {
        "task_id": task.task_id,
        "module": task.module,
        "source_path": str(task.source),
        "source_relative_path": str(task.source.relative_to(dataset_dir)),
        "source_sha256": task.source_sha256,
        "source_bytes": task.source_bytes,
        "source_lines": task.source_lines,
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_split(
    output_dir: Path,
    dataset_dir: Path,
    tasks: list[Task],
    groups: list[list[int]],
    edges: list[dict[str, object]],
    similarities: dict[tuple[int, int], tuple[float, float]],
    train_indices: set[int],
    seed: int,
    source_threshold: float,
    proof_delta_threshold: float,
    force: bool,
) -> None:
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    heldout_indices = set(range(len(tasks))) - train_indices
    train_tasks = [tasks[index] for index in sorted(train_indices, key=lambda i: tasks[i].task_id)]
    heldout_tasks = [tasks[index] for index in sorted(heldout_indices, key=lambda i: tasks[i].task_id)]
    if len(train_tasks) != 77 or len(heldout_tasks) != 77:
        raise AssertionError("Split is not exactly 77/77")

    group_assignment: dict[int, str] = {}
    group_rows: list[dict[str, object]] = []
    for group_id, indices in enumerate(groups, start=1):
        assignments = {"train" if index in train_indices else "heldout" for index in indices}
        if len(assignments) != 1:
            raise AssertionError("A leakage group was split across train and held-out")
        assignment = assignments.pop()
        for index in indices:
            group_assignment[index] = assignment
        group_rows.append(
            {
                "group_id": f"G{group_id:03d}",
                "assignment": assignment,
                "size": len(indices),
                "task_ids": [tasks[index].task_id for index in indices],
            }
        )

    cross_pairs = [
        (left, right, values)
        for (left, right), values in similarities.items()
        if group_assignment[left] != group_assignment[right]
    ]
    max_source_pair = max(cross_pairs, key=lambda row: row[2][0])
    max_delta_pair = max(cross_pairs, key=lambda row: row[2][1])
    train_targets = {task.target for task in train_tasks}
    heldout_targets = {task.target for task in heldout_tasks}
    train_canonical = {task.canonical_target for task in train_tasks}
    heldout_canonical = {task.canonical_target for task in heldout_tasks}

    module_totals = Counter(task.module for task in tasks)
    module_train = Counter(task.module for task in train_tasks)
    module_heldout = Counter(task.module for task in heldout_tasks)
    manifest = {
        "experiment": "ironkv_claude_teacher_to_deepseek_trace2skill_77_77",
        "protocol": "cross_model_trace2skill_style_distillation",
        "dataset_dir": str(dataset_dir),
        "dataset_task_count": len(tasks),
        "train_count": len(train_tasks),
        "heldout_count": len(heldout_tasks),
        "seed": seed,
        "grouping": {
            "same_target_name": True,
            "canonical_target_variants": [
                "_auto",
                "_temp",
                "-poly/send_packet_seq",
                "retransmit_un_acked_packets*",
            ],
            "source_normalized_token_shingle_width": 7,
            "source_jaccard_threshold": source_threshold,
            "proof_delta_normalized_token_shingle_width": 5,
            "proof_delta_jaccard_threshold": proof_delta_threshold,
            "component_count": len(groups),
            "component_sizes": dict(sorted(Counter(map(len, groups)).items())),
        },
        "module_distribution": {
            module: {
                "total": module_totals[module],
                "train": module_train[module],
                "heldout": module_heldout[module],
            }
            for module in sorted(module_totals)
        },
        "artifact_policy": {
            "train_manifest_includes": ["source", "trajectory", "verified_solution"],
            "heldout_manifest_includes": ["source_only"],
            "heldout_trajectory_and_verified_solution_must_not_be_mounted_or_passed_to_agent": True,
        },
        "files": {
            "train": "train_trajectories.jsonl",
            "heldout": "heldout_tasks.jsonl",
            "train_ids": "train_ids.txt",
            "heldout_ids": "heldout_ids.txt",
            "leakage_audit": "leakage_audit.json",
        },
    }
    audit = {
        "status": "PASS",
        "checks": {
            "complete_triplets": True,
            "exact_77_77": True,
            "task_id_overlap_count": 0,
            "source_sha256_overlap_count": len(
                {task.source_sha256 for task in train_tasks}
                & {task.source_sha256 for task in heldout_tasks}
            ),
            "exact_target_name_overlap": sorted(train_targets & heldout_targets),
            "canonical_target_overlap": sorted(train_canonical & heldout_canonical),
            "leakage_component_split_count": 0,
            "heldout_public_manifest_exposes_trajectory": False,
            "heldout_public_manifest_exposes_verified_solution": False,
            "cross_split_max_source_similarity": {
                "value": round(max_source_pair[2][0], 6),
                "left": tasks[max_source_pair[0]].task_id,
                "right": tasks[max_source_pair[1]].task_id,
                "required_below": source_threshold,
            },
            "cross_split_max_proof_delta_similarity": {
                "value": round(max_delta_pair[2][1], 6),
                "left": tasks[max_delta_pair[0]].task_id,
                "right": tasks[max_delta_pair[1]].task_id,
                "required_below": proof_delta_threshold,
            },
        },
        "leakage_edges": edges,
        "groups": group_rows,
        "limitations": [
            "No automatic similarity rule can prove semantic independence.",
            "All tasks come from one codebase and necessarily share IronKV definitions.",
            "Verified solutions are used only offline to group similar proof deltas; they must never be exposed to held-out agents.",
        ],
    }
    critical_values = audit["checks"]
    if (
        critical_values["source_sha256_overlap_count"] != 0
        or critical_values["exact_target_name_overlap"]
        or critical_values["canonical_target_overlap"]
        or max_source_pair[2][0] >= source_threshold
        or max_delta_pair[2][1] >= proof_delta_threshold
    ):
        raise AssertionError("Leakage audit failed")

    write_json(output_dir / "split_manifest.json", manifest)
    write_jsonl(
        output_dir / "train_trajectories.jsonl",
        (public_train_record(task, dataset_dir) for task in train_tasks),
    )
    write_jsonl(
        output_dir / "heldout_tasks.jsonl",
        (public_heldout_record(task, dataset_dir) for task in heldout_tasks),
    )
    (output_dir / "train_ids.txt").write_text(
        "\n".join(task.task_id for task in train_tasks) + "\n", encoding="utf-8"
    )
    (output_dir / "heldout_ids.txt").write_text(
        "\n".join(task.task_id for task in heldout_tasks) + "\n", encoding="utf-8"
    )
    write_json(output_dir / "leakage_audit.json", audit)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "split",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--source-threshold", type=float, default=DEFAULT_SOURCE_THRESHOLD)
    parser.add_argument(
        "--proof-delta-threshold", type=float, default=DEFAULT_PROOF_DELTA_THRESHOLD
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_dir = args.dataset_dir.resolve()
    output_dir = args.output_dir.resolve()
    tasks = discover_tasks(dataset_dir)
    if len(tasks) != 154:
        raise ValueError(f"Expected 154 IronKV tasks, found {len(tasks)}")
    groups, edges, similarities = build_groups(
        tasks, args.source_threshold, args.proof_delta_threshold
    )
    train_indices = choose_split(groups, tasks, 77, args.seed)
    write_split(
        output_dir,
        dataset_dir,
        tasks,
        groups,
        edges,
        similarities,
        train_indices,
        args.seed,
        args.source_threshold,
        args.proof_delta_threshold,
        args.force,
    )
    print(f"Wrote leakage-aware split: {output_dir}")
    print("train=77 heldout=77 status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

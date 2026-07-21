from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from verus_self_evolve.data import ATTEMPT_RE, load_traces, sha256_file
from verus_self_evolve.data_layout import validate_output_path
from verus_self_evolve.models import Trace


RAW_DIR_NAMES = (
    "all_batch_results-cyy-claude",
    "all_batch_results-cyy-claude-s4",
    "all_batch_results-cyy-gpt5",
    "all_batch_results-cyy-o4mini",
)
STATUSES = ("FAILED", "TIMEOUT", "VERIFIED")

AGENT_RE = re.compile(r"Using\s+([A-Za-z0-9_]+Agent)\s+for repair")
CURRENT_SCORE_RE = re.compile(r"Current score:\s*(.*)")
ERROR_BLOCK_RE = re.compile(
    r"Error text:\s*(.*?)(?=\n.*?Using\s+[A-Za-z0-9_]+Agent\s+for repair)",
    re.DOTALL,
)
PRIMARY_ACTION_RE = re.compile(r"['\"]primary_action['\"]:\s*['\"]([^'\"]+)['\"]")
REASONING_RE = re.compile(r"['\"]reasoning['\"]:\s*['\"]([^'\"]+)", re.DOTALL)
REJECTION_RE = re.compile(r"Candidate\s+\d+\s+rejected:\s*([^\n]+)")


def ensure_safe_output(data_root: Path, out_dir: Path) -> None:
    output = out_dir.resolve()
    for name in RAW_DIR_NAMES:
        raw = (data_root / name).resolve()
        if output == raw or raw in output.parents:
            raise ValueError(f"output directory must not be inside raw trace data: {output}")


def stable_key(seed: str, trace: Trace) -> str:
    value = f"{seed}\0{trace.status}\0{trace.model}\0{trace.file}"
    return hashlib.sha256(value.encode()).hexdigest()


def allocate_per_model(total: int, models: list[str]) -> dict[str, int]:
    base, remainder = divmod(total, len(models))
    return {model: base + (index < remainder) for index, model in enumerate(models)}


def select_traces(
    traces: Iterable[Trace],
    quotas: dict[str, int],
    used_tasks: set[str],
    seed: str,
) -> list[Trace]:
    traces = list(traces)
    models = sorted({trace.model for trace in traces})
    selected: list[Trace] = []
    for status in STATUSES:
        per_model = allocate_per_model(quotas.get(status, 0), models)
        for model in models:
            if per_model[model] == 0:
                continue
            candidates = sorted(
                (
                    trace
                    for trace in traces
                    if trace.status == status
                    and trace.model == model
                    and trace.file not in used_tasks
                ),
                key=lambda trace: stable_key(seed, trace),
            )
            chosen: list[Trace] = []
            for trace in candidates:
                if trace.file in used_tasks:
                    continue
                chosen.append(trace)
                used_tasks.add(trace.file)
                if len(chosen) == per_model[model]:
                    break
            if len(chosen) != per_model[model]:
                raise ValueError(
                    f"not enough unique tasks for status={status}, model={model}: "
                    f"needed {per_model[model]}, found {len(chosen)}"
                )
            selected.extend(chosen)
    return selected


def strip_log_prefix(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if " - " in line:
            line = line.split(" - ", 1)[1]
        lines.append(line.rstrip())
    return "\n".join(lines)


def excerpt(value: str, limit: int) -> str:
    value = "\n".join(line.rstrip() for line in value.strip().splitlines())
    return value if len(value) <= limit else value[:limit].rstrip() + " ..."


def attempt_summary(chunk: str, index: int) -> str:
    clean = strip_log_prefix(chunk)
    lines = [f"=== ATTEMPT {index} ==="]

    score = CURRENT_SCORE_RE.search(clean)
    if score:
        lines.append(f"[VERIFIER BEFORE] {score.group(1).strip()}")

    target = re.search(r"Target error:\s*(?:VerusErrorType\.)?([A-Za-z0-9_]+)", clean)
    if target:
        lines.append(f"[TARGET ERROR] {target.group(1)}")

    error = ERROR_BLOCK_RE.search(clean)
    if error:
        lines.append(f"[ERROR EVIDENCE]\n{excerpt(error.group(1), 700)}")

    agent = AGENT_RE.search(clean)
    if agent:
        lines.append(f"[Agent_{agent.group(1)}]")

    action = PRIMARY_ACTION_RE.search(clean)
    if action:
        lines.append(f"[PRIMARY ACTION] {action.group(1)}")

    reasoning = REASONING_RE.search(clean)
    if reasoning:
        lines.append(f"[REASONING SUMMARY] {excerpt(reasoning.group(1), 500)}")

    rejections = REJECTION_RE.findall(clean)
    for reason in rejections[:3]:
        lines.append(f"[CANDIDATE REJECTED] {reason.strip()}")

    if "Candidate 1 accepted" in clean or "Action accepted" in clean:
        lines.append("[LOCAL ACCEPTANCE] candidate accepted by repair harness")
    if "Repair accepted (version" in clean:
        version = re.search(r"Repair accepted \(version\s+(\d+)\)", clean)
        lines.append(
            f"[VERSION UPDATE] accepted version {version.group(1) if version else 'unknown'}"
        )
    if "Repair failed to generate new code" in clean:
        lines.append("[NO PROGRESS] repair failed to generate an accepted version")

    tail_events = []
    for pattern in (
        r"All errors fixed[^\n]*",
        r"Max repair attempts[^\n]*",
        r"Repair process timed out[^\n]*",
        r"Final verification[^\n]*",
    ):
        tail_events.extend(re.findall(pattern, clean, re.IGNORECASE))
    for event in tail_events[:3]:
        lines.append(f"[TERMINATION EVIDENCE] {event.strip()}")
    return "\n".join(lines)


def build_trajectory(trace: Trace) -> tuple[str, list[str]]:
    log_path = Path(trace.log_path)
    text = log_path.read_text(errors="replace")
    matches = list(ATTEMPT_RE.finditer(text))
    agents = sorted(set(AGENT_RE.findall(text)))

    parts = [
        "[SYSTEM] VeruSAGE hierarchical Verus proof-repair run",
        "[Agent_RepairOrchestrator] selects a specialized repair agent from verifier feedback,",
        "then the Verus verifier and safety checks accept or reject candidate proof edits.",
        f"[TASK] Repair {trace.file} (project {trace.project}).",
    ]
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        parts.append(attempt_summary(text[match.start():end], int(match.group(1))))
    parts.append(
        f"[FINAL OUTCOME] task-level results.csv status={trace.status}; "
        "local accepted steps above do not imply task success."
    )
    return "\n\n".join(parts), agents


def to_atlas_record(trace: Trace) -> dict[str, object]:
    trajectory, agents = build_trajectory(trace)
    return {
        "problem_id": f"{trace.model}:{trace.file}",
        "task": f"Repair a Verus proof task in project {trace.project}: {trace.file}",
        "raw_trajectory": trajectory,
        "metadata": {
            "mas_name": "VeruSAGE",
            "llm_name": trace.model,
            "benchmark_name": "local Verusage trace corpus snapshot",
            "trace_id": f"{trace.model}:{trace.batch}:{trace.file}",
            "project": trace.project,
            "batch": trace.batch,
            "outcome": trace.status,
            "agents_seen": [],
            "_format": "verusage_atlas_adapter_v1",
            "source_ref": trace.log_path,
        },
    }


def write_jsonl(path: Path, records: Iterable[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def write_split(out_dir: Path, name: str, traces: list[Trace]) -> dict[str, object]:
    records = [to_atlas_record(trace) for trace in traces]
    write_jsonl(out_dir / f"{name}.jsonl", records)
    return {
        "trace_count": len(traces),
        "unique_task_count": len({trace.file for trace in traces}),
        "status_counts": dict(sorted(Counter(trace.status for trace in traces).items())),
        "model_counts": dict(sorted(Counter(trace.model for trace in traces).items())),
        "project_counts": dict(sorted(Counter(trace.project for trace in traces).items())),
        "records": [
            {
                "problem_id": record["problem_id"],
                "status": trace.status,
                "source_ref": trace.log_path,
                "source_sha256": sha256_file(Path(trace.log_path)),
            }
            for trace, record in zip(traces, records)
        ],
    }


def parse_quota(value: str) -> dict[str, int]:
    values = {status: 0 for status in STATUSES}
    for item in value.split(","):
        status, count = item.split("=", 1)
        status = status.strip().upper()
        if status not in values:
            raise argparse.ArgumentTypeError(f"unknown status in quota: {status}")
        values[status] = int(count)
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare leakage-safe ATLAS inputs from VeruSAGE traces")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", default="atlas-verusage-v1")
    parser.add_argument("--train-quota", type=parse_quota, default=parse_quota("FAILED=20,TIMEOUT=12,VERIFIED=8"))
    parser.add_argument("--eval-quota", type=parse_quota, default=parse_quota("FAILED=4,TIMEOUT=4,VERIFIED=4"))
    args = parser.parse_args()

    args.out = validate_output_path(args.out, data_root=args.data_root)
    ensure_safe_output(args.data_root, args.out)
    traces = load_traces(args.data_root)
    used_tasks: set[str] = set()
    train = select_traces(traces, args.train_quota, used_tasks, args.seed + ":train")
    evaluation = select_traces(traces, args.eval_quota, used_tasks, args.seed + ":eval")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "adapter_version": 1,
        "data_root": str(args.data_root.resolve()),
        "raw_data_read_only": True,
        "source_trace_count": len(traces),
        "seed": args.seed,
        "split_contract": "normalized task ids are disjoint across train/eval and within each split",
        "known_deviations": [
            "ATLAS receives a compact evidence-preserving rendering, not the byte-for-byte raw log.",
            "Task-level results.csv outcome is appended explicitly; local accepted steps remain separately labeled.",
            "The adapter pre-tags the hierarchical orchestrator and specialized repair agents for role discovery.",
        ],
        "train": write_split(args.out, "train", train),
        "eval": write_split(args.out, "eval", evaluation),
    }
    overlap = {trace.file for trace in train} & {trace.file for trace in evaluation}
    if overlap:
        raise AssertionError(f"task leakage detected: {sorted(overlap)[:3]}")
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: manifest[key] for key in ("adapter_version", "train", "eval")}, indent=2))


if __name__ == "__main__":
    main()

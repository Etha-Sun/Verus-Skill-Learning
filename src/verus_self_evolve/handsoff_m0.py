from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .data_layout import selected_dataset_path


DIRECTORY_SPLITS: dict[str, dict[str, Any]] = {
    "verified-anvil": {"split": "train", "project_codes": ["AC", "AL"]},
    "verified-ironkv": {"split": "train", "project_codes": ["IR"]},
    "verified-atmo": {"split": "dev", "project_codes": ["OS", "ST"]},
    "verified-storage": {"split": "dev", "project_codes": ["OS", "ST"]},
    "verified-node-replication": {"split": "dev", "project_codes": ["NO"]},
    "verified-vest": {"split": "dev", "project_codes": ["VE"]},
    "verified-memory-allocator": {"split": "test", "project_codes": ["MA"]},
    "verified-nrkernel": {"split": "test", "project_codes": ["NR"]},
}
PROJECT_SPLITS = {
    code: spec["split"]
    for spec in DIRECTORY_SPLITS.values()
    for code in spec["project_codes"]
}

USAGE_LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)\s+"
    r"([0-9.]+[kKmM]?)\s+input,\s+"
    r"([0-9.]+[kKmM]?)\s+output,\s+"
    r"([0-9.]+[kKmM]?)\s+cache read"
    r"(?:\s+\(Est\.[^)]*\))?\s*$",
    re.MULTILINE,
)
PREMIUM_RE = re.compile(r"Total usage est:\s*([0-9.]+)\s+Premium requests")
DURATION_RE = re.compile(r"Total duration \((API|wall)\):\s*([^\n]+)")
CURRENT_USAGE_RE = re.compile(
    r"^\s*Tokens\s+↑\s*([0-9.]+[kKmM]?)\s*•\s*"
    r"↓\s*([0-9.]+[kKmM]?)\s*•\s*"
    r"([0-9.]+[kKmM]?)\s*\(cached\)\s*$",
    re.MULTILINE,
)
CURRENT_DURATION_RE = re.compile(r"^\s*Duration\s+([^\n]+)$", re.MULTILINE)
CODE_FENCE_RE = re.compile(r"~~~(?:rust|verus)?\s*\n([\s\S]*?)\n~~~")
BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
LINE_COMMENT_RE = re.compile(r"//[^\n]*")
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\s]")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_code(text: str) -> str:
    text = BLOCK_COMMENT_RE.sub("", text)
    text = LINE_COMMENT_RE.sub("", text)
    return "".join(text.split())


def normalized_code_sha256(text: str) -> str:
    return _sha256_bytes(normalize_code(text).encode("utf-8"))


def normalize_task_id(task_id: str) -> str:
    task_id = task_id.removesuffix("_verified")
    task_id = re.sub(r"^[A-Z]{2}__", "", task_id)
    return re.sub(r"[^a-z0-9]+", "_", task_id.lower()).strip("_")


def parse_scaled_number(value: str) -> int:
    multiplier = 1
    suffix = value[-1:].lower()
    if suffix == "k":
        multiplier = 1_000
        value = value[:-1]
    elif suffix == "m":
        multiplier = 1_000_000
        value = value[:-1]
    return int(round(float(value) * multiplier))


def parse_duration_seconds(value: str) -> float | None:
    value = value.strip()
    match = re.fullmatch(
        r"(?:(\d+)h\s*)?(?:(\d+)m\s*)?([0-9.]+)s",
        value,
    )
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def parse_copilot_usage(text: str) -> dict[str, Any]:
    by_model = []
    for match in USAGE_LINE_RE.finditer(text):
        by_model.append(
            {
                "model": match.group(1),
                "input_tokens": parse_scaled_number(match.group(2)),
                "output_tokens": parse_scaled_number(match.group(3)),
                "cache_read_tokens": parse_scaled_number(match.group(4)),
            }
        )
    if not by_model:
        current = CURRENT_USAGE_RE.search(text)
        if current:
            by_model.append(
                {
                    "model": "copilot-total",
                    "input_tokens": parse_scaled_number(current.group(1)),
                    "output_tokens": parse_scaled_number(current.group(2)),
                    "cache_read_tokens": parse_scaled_number(current.group(3)),
                }
            )
    durations: dict[str, float | None] = {}
    for match in DURATION_RE.finditer(text):
        durations[f"{match.group(1).lower()}_seconds"] = parse_duration_seconds(
            match.group(2)
        )
    if "wall_seconds" not in durations:
        current_duration = CURRENT_DURATION_RE.search(text)
        if current_duration:
            durations["wall_seconds"] = parse_duration_seconds(
                current_duration.group(1)
            )
    premium = PREMIUM_RE.search(text)
    totals = {
        "input_tokens": sum(row["input_tokens"] for row in by_model),
        "output_tokens": sum(row["output_tokens"] for row in by_model),
        "cache_read_tokens": sum(row["cache_read_tokens"] for row in by_model),
    }
    totals["uncached_input_tokens"] = max(
        totals["input_tokens"] - totals["cache_read_tokens"], 0
    )
    totals["uncached_total_tokens"] = (
        totals["uncached_input_tokens"] + totals["output_tokens"]
    )
    return {
        "available": bool(by_model),
        "premium_requests": float(premium.group(1)) if premium else None,
        "by_model": by_model,
        "totals": totals,
        **durations,
    }


def infer_model(result_dir: str) -> str:
    value = result_dir.lower()
    if "opus45" in value:
        return "claude-opus-4.5"
    if "sonnet45" in value or re.search(r"(?:^|-)s45(?:-|$)", value):
        return "claude-sonnet-4.5"
    if "sonnet4" in value or re.search(r"(?:^|-)s4(?:-|$)", value):
        return "claude-sonnet-4"
    if "gpt5" in value:
        return "gpt-5"
    if "o4" in value:
        return "o4"
    return "unknown"


def infer_variant(result_dir: str) -> str:
    value = result_dir.lower()
    flags = []
    if "advanced" in value or "adv" in value:
        flags.append("advanced")
    if "nolemma" in value or "nol" in value:
        flags.append("no_lemma")
    if "del" in value:
        flags.append("deletion")
    if "hard" in value:
        flags.append("hard")
    return "+".join(flags) if flags else "standard"


def _path_metadata(path: Path) -> dict[str, Any]:
    if path.exists():
        stat = path.stat()
        return {"path": str(path), "size_bytes": stat.st_size}
    return {"path": None, "size_bytes": None}


def _content_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"sha256": None, "normalized_code_sha256": None}
    text = path.read_text(errors="replace")
    return {
        "sha256": sha256_file(path),
        "normalized_code_sha256": normalized_code_sha256(text),
    }


def inventory_row(corpus_root: Path, log_path: Path) -> dict[str, Any]:
    relative = log_path.relative_to(corpus_root)
    group = relative.parts[0]
    split_spec = DIRECTORY_SPLITS.get(
        group, {"split": "excluded", "project_codes": []}
    )
    split = split_spec["split"]
    result_dir = relative.parts[1] if len(relative.parts) > 1 else ""
    source_path = log_path.with_suffix(".rs")
    verified_path = log_path.with_name(f"{log_path.stem}_verified.rs")
    content_scanned = split == "train"

    row: dict[str, Any] = {
        "trace_id": _sha256_bytes(str(relative).encode("utf-8"))[:20],
        "relative_log_path": str(relative),
        "directory_group": group,
        "split": split,
        "project_codes": split_spec["project_codes"],
        "result_dir": result_dir,
        "model": infer_model(result_dir),
        "variant": infer_variant(result_dir),
        "task_id": log_path.stem,
        "normalized_task_id": normalize_task_id(log_path.stem),
        "log_size_bytes": log_path.stat().st_size,
        "source": _path_metadata(source_path),
        "verified": _path_metadata(verified_path),
        "content_scanned": content_scanned,
        "log_sha256": None,
        "usage": None,
    }
    row["source"].update({"sha256": None, "normalized_code_sha256": None})
    row["verified"].update({"sha256": None, "normalized_code_sha256": None})
    if content_scanned:
        text = log_path.read_text(errors="replace")
        row["log_sha256"] = sha256_file(log_path)
        row["usage"] = parse_copilot_usage(text)
        row["source"].update(_content_metadata(source_path))
        row["verified"].update(_content_metadata(verified_path))
    return row


def _ensure_output_outside_corpus(corpus_root: Path, out_dir: Path) -> None:
    corpus = corpus_root.resolve()
    output = out_dir.resolve()
    if output == corpus or corpus in output.parents:
        raise ValueError("output directory must be outside the raw corpus")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_inventory(corpus_root: Path, out_dir: Path) -> dict[str, Any]:
    _ensure_output_outside_corpus(corpus_root, out_dir)
    rows = [
        inventory_row(corpus_root, path)
        for path in sorted(corpus_root.glob("verified-*/*/*.log"))
    ]
    split_counts = Counter(row["split"] for row in rows)
    group_counts = Counter(row["directory_group"] for row in rows)
    model_counts = Counter(row["model"] for row in rows)
    task_groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        task_groups[
            f"{row['directory_group']}::{row['normalized_task_id']}"
        ].append(row["trace_id"])
    duplicate_groups = {
        key: trace_ids for key, trace_ids in task_groups.items() if len(trace_ids) > 1
    }
    summary = {
        "created_at": _now(),
        "corpus_root": str(corpus_root.resolve()),
        "read_only_contract": True,
        "glob": "verified-*/*/*.log",
        "corpus_log_count": len(rows),
        "split_counts": dict(sorted(split_counts.items())),
        "directory_group_counts": dict(sorted(group_counts.items())),
        "model_counts": dict(sorted(model_counts.items())),
        "unique_task_groups": len(task_groups),
        "duplicate_task_group_count": len(duplicate_groups),
        "train_content_scanned": sum(row["content_scanned"] for row in rows),
        "sealed_content_scanned": sum(
            row["content_scanned"] and row["split"] == "test" for row in rows
        ),
        "train_usage_available": sum(
            bool(row["usage"] and row["usage"]["available"]) for row in rows
        ),
        "excluded_directory_groups": sorted(
            group for group in group_counts if group not in DIRECTORY_SPLITS
        ),
    }
    _write_jsonl(out_dir / "corpus_manifest.jsonl", rows)
    _write_json(out_dir / "corpus_summary.json", summary)
    _write_json(
        out_dir / "duplicate_groups.json",
        {
            "created_at": _now(),
            "group_count": len(duplicate_groups),
            "groups": duplicate_groups,
        },
    )
    return summary


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _extract_prompt_code(item: dict[str, Any]) -> str:
    messages = item.get("prompt_messages") or []
    content = messages[0].get("content", "") if messages else ""
    matches = CODE_FENCE_RE.findall(content.replace(chr(96) * 3, "~~~"))
    return max(matches, key=len) if matches else ""


def _code_shingles(text: str, width: int = 7) -> set[tuple[str, ...]]:
    tokens = TOKEN_RE.findall(normalize_code(text))
    if len(tokens) < width:
        return {tuple(tokens)} if tokens else set()
    return {
        tuple(tokens[index : index + width])
        for index in range(len(tokens) - width + 1)
    }


def _jaccard(left: set[Any], right: set[Any]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def run_leakage_audit(
    manifest_path: Path,
    eval_path: Path,
    out_dir: Path,
    near_threshold: float = 0.90,
) -> dict[str, Any]:
    manifest_rows = _load_jsonl(manifest_path)
    eval_items = _load_jsonl(eval_path)
    eval_rows = []
    eval_code_by_id: dict[str, str] = {}
    for item in eval_items:
        meta = item.get("meta") or {}
        project = str(meta.get("project") or "")
        task_id = str(meta.get("task_id") or meta.get("rel_path") or "")
        normalized_id = normalize_task_id(task_id)
        code = _extract_prompt_code(item)
        eval_id = _sha256_bytes(f"{project}::{normalized_id}".encode())[:20]
        split = PROJECT_SPLITS.get(project, "excluded")
        eval_rows.append(
            {
                "eval_id": eval_id,
                "project": project,
                "split": split,
                "task_id": task_id,
                "normalized_task_id": normalized_id,
                "prompt_code_available": bool(code),
                "prompt_code_sha256": normalized_code_sha256(code) if code else None,
            }
        )
        if code:
            eval_code_by_id[eval_id] = code

    train_rows_by_source: dict[str, dict[str, Any]] = {}
    for row in manifest_rows:
        if row["split"] != "train" or not row["content_scanned"]:
            continue
        source_hash = row["source"].get("normalized_code_sha256")
        source_path = row["source"].get("path")
        if source_hash and source_path:
            train_rows_by_source.setdefault(source_hash, row)

    test_eval = [row for row in eval_rows if row["split"] == "test"]
    train_names = {
        row["normalized_task_id"]
        for row in manifest_rows
        if row["split"] == "train"
    }
    exact_name_pairs = [
        {
            "eval_id": row["eval_id"],
            "project": row["project"],
            "normalized_task_id": row["normalized_task_id"],
        }
        for row in test_eval
        if row["normalized_task_id"] in train_names
    ]
    train_hashes = set(train_rows_by_source)
    exact_code_pairs = [
        {
            "eval_id": row["eval_id"],
            "project": row["project"],
            "normalized_task_id": row["normalized_task_id"],
            "normalized_code_sha256": row["prompt_code_sha256"],
        }
        for row in test_eval
        if row["prompt_code_sha256"] in train_hashes
    ]

    train_shingles = []
    for source_hash, row in train_rows_by_source.items():
        source_text = Path(row["source"]["path"]).read_text(errors="replace")
        train_shingles.append(
            (
                source_hash,
                row["normalized_task_id"],
                row["directory_group"],
                _code_shingles(source_text),
            )
        )
    near_pairs = []
    for eval_row in test_eval:
        eval_text = eval_code_by_id.get(eval_row["eval_id"], "")
        eval_shingles = _code_shingles(eval_text)
        best: dict[str, Any] | None = None
        for source_hash, task_id, group, shingles in train_shingles:
            score = _jaccard(eval_shingles, shingles)
            if best is None or score > best["jaccard_7gram"]:
                best = {
                    "eval_id": eval_row["eval_id"],
                    "eval_project": eval_row["project"],
                    "eval_task_id": eval_row["normalized_task_id"],
                    "train_directory_group": group,
                    "train_task_id": task_id,
                    "train_source_hash": source_hash,
                    "jaccard_7gram": score,
                }
        if best and best["jaccard_7gram"] >= near_threshold:
            near_pairs.append(best)

    split_manifest = {
        "created_at": _now(),
        "status": "frozen_pre_outcome",
        "directory_splits": DIRECTORY_SPLITS,
        "project_splits": PROJECT_SPLITS,
        "corpus_manifest_path": str(manifest_path.resolve()),
        "corpus_manifest_sha256": sha256_file(manifest_path),
        "evaluation_path": str(eval_path.resolve()),
        "evaluation_sha256": sha256_file(eval_path),
        "evaluation_tasks": eval_rows,
        "sealed_projects": sorted(
            project for project, split in PROJECT_SPLITS.items() if split == "test"
        ),
        "sealed_corpus_content_used": False,
        "evaluation_answers_accessed": False,
    }
    report = {
        "created_at": _now(),
        "near_threshold": near_threshold,
        "train_unique_source_count": len(train_rows_by_source),
        "test_eval_task_count": len(test_eval),
        "test_prompt_code_available": sum(
            row["prompt_code_available"] for row in test_eval
        ),
        "exact_train_test_name_overlap_count": len(exact_name_pairs),
        "exact_train_test_code_overlap_count": len(exact_code_pairs),
        "near_train_test_overlap_count": len(near_pairs),
        "exact_name_pairs": exact_name_pairs,
        "exact_code_pairs": exact_code_pairs,
        "near_pairs": sorted(
            near_pairs, key=lambda row: row["jaccard_7gram"], reverse=True
        ),
        "sealed_corpus_content_scanned": 0,
        "evaluation_answers_accessed": False,
    }
    report["verdict"] = (
        "PASS"
        if not exact_name_pairs and not exact_code_pairs and not near_pairs
        else "REVIEW"
    )
    metric_contract = {
        "created_at": _now(),
        "stage": "M0",
        "required_metric_keys": [
            "corpus_log_count",
            "train_content_scanned",
            "sealed_content_scanned",
            "exact_train_test_overlap_count",
            "near_train_test_overlap_count",
            "harness_unit_tests_passed",
            "smoke_usage_available",
            "smoke_verus_checked",
            "smoke_checker_checked",
        ],
        "definitions": {
            "exact_train_test_overlap_count": (
                "exact normalized task-name or normalized source-code overlaps"
            ),
            "near_train_test_overlap_count": (
                f"7-token-shingle Jaccard >= {near_threshold}"
            ),
        },
    }
    _write_json(out_dir / "split_manifest.json", split_manifest)
    _write_json(out_dir / "leakage_report.json", report)
    _write_json(out_dir / "metric_contract.json", metric_contract)
    return report


def apply_leakage_quarantine(
    manifest_path: Path,
    leakage_report_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    rows = _load_jsonl(manifest_path)
    source_manifest_path = str(manifest_path.resolve())
    source_manifest_sha256 = sha256_file(manifest_path)
    report = json.loads(leakage_report_path.read_text())
    task_ids = {
        pair["normalized_task_id"] for pair in report.get("exact_name_pairs", [])
    }
    task_ids.update(
        pair["train_task_id"] for pair in report.get("near_pairs", [])
    )
    source_hashes = {
        pair["train_source_hash"] for pair in report.get("near_pairs", [])
    }
    quarantined_trace_ids = []
    quarantined_task_ids = set()
    effective_rows = []
    for row in rows:
        should_quarantine = row.get("split") == "train" and (
            row.get("normalized_task_id") in task_ids
            or row.get("source", {}).get("normalized_code_sha256") in source_hashes
        )
        effective_row = dict(row)
        if should_quarantine:
            effective_row["split"] = "quarantine"
            effective_row["quarantine_reason"] = "sealed_eval_name_or_code_overlap"
            quarantined_trace_ids.append(row["trace_id"])
            quarantined_task_ids.add(row["normalized_task_id"])
        effective_rows.append(effective_row)

    if report.get("verdict") != "PASS" and not quarantined_trace_ids:
        raise ValueError("leakage report requires review but matched no train traces")

    effective_manifest = out_dir / "effective_corpus_manifest.jsonl"
    _write_jsonl(effective_manifest, effective_rows)
    quarantine = {
        "created_at": _now(),
        "source_manifest_path": source_manifest_path,
        "source_manifest_sha256": source_manifest_sha256,
        "source_leakage_report_path": str(leakage_report_path.resolve()),
        "source_leakage_report_sha256": sha256_file(leakage_report_path),
        "quarantine_reason": "sealed_eval_name_or_code_overlap",
        "quarantined_trace_count": len(quarantined_trace_ids),
        "quarantined_task_count": len(quarantined_task_ids),
        "quarantined_task_ids": sorted(quarantined_task_ids),
        "quarantined_trace_ids": sorted(quarantined_trace_ids),
        "effective_manifest_path": str(effective_manifest.resolve()),
        "effective_manifest_sha256": sha256_file(effective_manifest),
    }
    _write_json(out_dir / "quarantine_report.json", quarantine)
    return quarantine


def main() -> None:
    parser = argparse.ArgumentParser(prog="handsoff-m0")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory_parser = subparsers.add_parser("inventory")
    inventory_parser.add_argument(
        "--corpus-root",
        type=Path,
        help="hands-off corpus root; defaults to the locally selected source",
    )
    inventory_parser.add_argument("--out-dir", type=Path, required=True)
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--manifest", type=Path, required=True)
    audit_parser.add_argument("--eval", dest="eval_path", type=Path, required=True)
    audit_parser.add_argument("--out-dir", type=Path, required=True)
    audit_parser.add_argument("--near-threshold", type=float, default=0.90)
    quarantine_parser = subparsers.add_parser("quarantine")
    quarantine_parser.add_argument("--manifest", type=Path, required=True)
    quarantine_parser.add_argument("--leakage-report", type=Path, required=True)
    quarantine_parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "inventory":
        corpus_root = args.corpus_root or selected_dataset_path("handsoff")
        summary = build_inventory(corpus_root, args.out_dir)
        print(json.dumps(summary, indent=2))
    elif args.command == "audit":
        report = run_leakage_audit(
            args.manifest,
            args.eval_path,
            args.out_dir,
            near_threshold=args.near_threshold,
        )
        print(json.dumps(report, indent=2))
    else:
        report = apply_leakage_quarantine(
            args.manifest,
            args.leakage_report,
            args.out_dir,
        )
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

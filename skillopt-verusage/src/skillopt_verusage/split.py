from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


ALLOWED_GROUPS = ("verified-anvil", "verified-ironkv")
QUOTAS = {
    "small": {"train": 7, "val": 3, "test": 7},
    "medium": {"train": 7, "val": 3, "test": 7},
    "large": {"train": 6, "val": 4, "test": 6},
}
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|\S")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized_task(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _shingles(text: str, n: int = 7) -> set[str]:
    tokens = TOKEN_RE.findall(text)
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / max(1, len(left | right))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _external_empty(path: Path) -> Path:
    root_text = os.environ.get("VERUS_SKILL_RUN_ROOT", "")
    if not root_text:
        raise ValueError("VERUS_SKILL_RUN_ROOT is not configured")
    root = Path(root_text).resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"split output must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    if resolved.exists() and any(resolved.iterdir()):
        raise ValueError(f"split output must be empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _candidate_rows(manifest: Path, corpus_root: Path) -> list[dict[str, Any]]:
    rows = _load_jsonl(manifest)
    by_task: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        group = str(row.get("directory_group") or "")
        task_id = str(row.get("task_id") or "")
        if (
            row.get("split") != "train"
            or row.get("variant") != "standard"
            or group not in ALLOWED_GROUPS
            or not task_id
            or Path(task_id).name != task_id
            or not (row.get("verified") or {}).get("sha256")
        ):
            continue
        key = (group, task_id)
        if key not in by_task or str(row.get("trace_id")) < str(
            by_task[key].get("trace_id")
        ):
            by_task[key] = row

    candidates: list[dict[str, Any]] = []
    for (group, task_id), row in by_task.items():
        source = (corpus_root / group / "unverified" / f"{task_id}.rs").resolve()
        allowed = (corpus_root / group / "unverified").resolve()
        if allowed not in source.parents or not source.is_file():
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        normalized = _normalized_task(str(row.get("normalized_task_id") or task_id))
        candidates.append(
            {
                "id": _stable(f"{group}::{normalized}::{_sha256_file(source)}")[:20],
                "task_id": task_id,
                "normalized_task_id": normalized,
                "directory_group": group,
                "source_path": str(source),
                "source_sha256": _sha256_file(source),
                "source_size_bytes": source.stat().st_size,
                "_shingles": _shingles(text),
            }
        )
    return candidates


def _r040_signatures(path: Path, corpus_root: Path) -> tuple[set[str], set[str], list[set[str]]]:
    tasks: set[str] = set()
    hashes: set[str] = set()
    shingles: list[set[str]] = []
    for row in _load_jsonl(path):
        group = str(row.get("directory_group") or "")
        if group not in ALLOWED_GROUPS:
            raise ValueError(f"forbidden R040 directory: {group}")
        tasks.add(_normalized_task(str(row.get("normalized_task_id") or row["task_id"])))
        metadata = row.get("source") or {}
        if metadata.get("sha256"):
            hashes.add(str(metadata["sha256"]))
        relative = str(metadata.get("path") or "")
        source = (corpus_root / relative).resolve()
        if source.is_file():
            shingles.append(_shingles(source.read_text(encoding="utf-8", errors="replace")))
    return tasks, hashes, shingles


def _assign_bins(rows: list[dict[str, Any]]) -> None:
    for group in ALLOWED_GROUPS:
        ordered = sorted(
            [row for row in rows if row["directory_group"] == group],
            key=lambda row: (row["source_size_bytes"], row["id"]),
        )
        for index, row in enumerate(ordered):
            row["size_bin"] = ("small", "medium", "large")[
                min(2, index * 3 // len(ordered))
            ]


def _precheck(
    row: dict[str, Any],
    verus_bin: Path,
    timeout: int,
) -> tuple[dict[str, Any], bool, dict[str, Any]]:
    try:
        completed = subprocess.run(
            [str(verus_bin), row["source_path"]],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout + completed.stderr
        passed = completed.returncode == 0 and "error: aborting" not in output.lower()
        summary = re.findall(
            r"verification results::\s*(\d+) verified,\s*(\d+) errors?",
            output,
            re.IGNORECASE,
        )
        check = {
            "returncode": completed.returncode,
            "timed_out": False,
            "passed": passed,
            "verified_count": int(summary[-1][0]) if summary else None,
            "error_count": int(summary[-1][1]) if summary else None,
        }
    except subprocess.TimeoutExpired:
        check = {
            "returncode": None,
            "timed_out": True,
            "passed": False,
            "verified_count": None,
            "error_count": None,
        }
    return row, bool(not check["passed"] and not check["timed_out"]), check


def freeze_split(
    *,
    manifest: Path,
    r040_selection: Path,
    corpus_root: Path,
    out_dir: Path,
    verus_bin: Path,
    workers: int = 8,
    near_threshold: float = 0.90,
) -> dict[str, Any]:
    out_dir = _external_empty(out_dir)
    candidates = _candidate_rows(manifest, corpus_root)
    excluded_tasks, excluded_hashes, excluded_shingles = _r040_signatures(
        r040_selection, corpus_root
    )
    eligible: list[dict[str, Any]] = []
    rejections: Counter[str] = Counter()
    for row in candidates:
        if row["normalized_task_id"] in excluded_tasks or row["source_sha256"] in excluded_hashes:
            rejections["r040_exact"] += 1
            continue
        similarity = max(
            (_jaccard(row["_shingles"], reference) for reference in excluded_shingles),
            default=0.0,
        )
        if similarity >= near_threshold:
            rejections["r040_near"] += 1
            continue
        row["r040_max_jaccard_7gram"] = round(similarity, 6)
        eligible.append(row)
    _assign_bins(eligible)

    selected: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    precheck_counts: Counter[str] = Counter()
    for group in ALLOWED_GROUPS:
        for size_bin, split_quotas in QUOTAS.items():
            pool = sorted(
                [
                    row
                    for row in eligible
                    if row["directory_group"] == group and row["size_bin"] == size_bin
                ],
                key=lambda row: _stable(f"split42::{row['id']}"),
            )
            needed = sum(split_quotas.values())
            failing: list[dict[str, Any]] = []
            for start in range(0, len(pool), workers):
                chunk = pool[start : start + workers]
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    checked = list(
                        executor.map(
                            lambda row: _precheck(row, verus_bin, 120),
                            chunk,
                        )
                    )
                for row, usable, check in checked:
                    if usable:
                        item = {
                            key: value
                            for key, value in row.items()
                            if not key.startswith("_")
                        }
                        item["source_precheck"] = check
                        failing.append(item)
                    else:
                        precheck_counts[
                            "source_timeout"
                            if check["timed_out"]
                            else "source_already_verified"
                        ] += 1
                if len(failing) >= needed:
                    break
            if len(failing) < needed:
                raise RuntimeError(
                    f"insufficient failing tasks for {group}/{size_bin}: "
                    f"{len(failing)} < {needed}"
                )
            cursor = 0
            for split_name, quota in split_quotas.items():
                selected[split_name].extend(failing[cursor : cursor + quota])
                cursor += quota

    all_ids = [row["id"] for rows in selected.values() for row in rows]
    if len(all_ids) != 100 or len(set(all_ids)) != 100:
        raise RuntimeError("frozen split is not 100 unique tasks")
    for split_name, rows in selected.items():
        split_path = out_dir / split_name
        split_path.mkdir()
        (split_path / "items.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    digest_payload = {
        split: [(row["id"], row["source_sha256"]) for row in rows]
        for split, rows in selected.items()
    }
    summary = {
        "schema_version": "1",
        "counts": {key: len(value) for key, value in selected.items()},
        "by_group": {
            split: dict(Counter(row["directory_group"] for row in rows))
            for split, rows in selected.items()
        },
        "by_size_bin": {
            split: dict(Counter(row["size_bin"] for row in rows))
            for split, rows in selected.items()
        },
        "split_sha256": _stable(json.dumps(digest_payload, sort_keys=True)),
        "near_threshold": near_threshold,
        "r040_rejections": dict(rejections),
        "source_precheck_rejections": dict(precheck_counts),
        "sealed_directories_read": [],
        "reference_content_exported": False,
    }
    (out_dir / "split_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--r040-selection", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    summary = freeze_split(**vars(args))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

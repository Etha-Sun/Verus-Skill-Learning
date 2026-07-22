from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .data_layout import validate_output_path
from .handsoff_calibration import _run_record, run_calibration_job
from .handsoff_m0 import sha256_file


CASES = ("pass", "closest_failure", "stalled")
FINAL_CASES = ("stable_pass", "stable_closest_failure", "unstable")
ALLOWED_TRACE_DIRECTORIES = ("verified-anvil", "verified-ironkv")
SIZE_ORDER = {"small": 0, "medium": 1, "large": 2}
LOCALIZED_FAILURE_RE = re.compile(
    r"assertion failed|postcondition not satisfied|precondition not satisfied",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _require_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"output directory must be empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _resolve_within(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    allowed = root.resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError(f"path escapes allowed root {allowed}: {resolved}")
    return resolved


def qualitative_label(
    task: dict[str, Any], run_dir: Path, repetition: int
) -> dict[str, Any]:
    record = _run_record(task, run_dir, repetition)
    label = record["outcome"]
    localized = False
    if label == "stalled":
        candidate = record.get("candidate_diagnostics") or {}
        source = record.get("source_diagnostics") or {}
        verus_log = run_dir / "verus.log"
        localized = bool(
            candidate.get("summary_found")
            and candidate.get("error_count") == 1
            and source.get("error_count") == 1
            and verus_log.is_file()
            and LOCALIZED_FAILURE_RE.search(verus_log.read_text(errors="replace"))
        )
        if localized:
            label = "closest_failure"
    return {**record, "qualitative_label": label, "localized_failure": localized}


def _diverse_pick(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    pools: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["directory_group"], row["source_size_bin"])
        pools.setdefault(key, []).append(row)
    for pool in pools.values():
        pool.sort(key=lambda row: (row["selection_rank"], row["calibration_id"]))
    selected: list[dict[str, Any]] = []
    strata = sorted(pools, key=lambda key: (SIZE_ORDER[key[1]], key[0]))
    while len(selected) < limit and any(pools.values()):
        for key in strata:
            if pools[key] and len(selected) < limit:
                selected.append(pools[key].pop(0))
    return selected


def select_qualitative_candidates(
    tasks_path: Path,
    runs_dir: Path,
    out_dir: Path,
    *,
    per_case: int = 3,
) -> dict[str, Any]:
    tasks = _load_jsonl(tasks_path)
    if len(tasks) != 30:
        raise ValueError(f"expected the frozen 30-task screen, got {len(tasks)}")
    records = []
    for task in tasks:
        run_dir = runs_dir / task["calibration_id"] / "rep_1" / "h0"
        records.append({**task, **qualitative_label(task, run_dir, 1)})
    if any(not row.get("result_available") for row in records):
        raise ValueError("the 30-task H0 screen is incomplete")

    selected = []
    for case in CASES:
        pool = [row for row in records if row["qualitative_label"] == case]
        if len(pool) < per_case:
            raise ValueError(f"insufficient {case} candidates: {len(pool)} < {per_case}")
        for row in _diverse_pick(pool, per_case):
            selected.append({**row, "candidate_case": case})

    _require_empty(out_dir)
    candidate_path = out_dir / "r040c_qualitative_candidates.jsonl"
    _write_jsonl(candidate_path, selected)
    jobs = [
        {
            "job_id": f"{row['calibration_id']}-rep{repetition}",
            "calibration_id": row["calibration_id"],
            "selection_rank": row["selection_rank"],
            "candidate_case": row["candidate_case"],
            "repetition": repetition,
            "condition": "h0",
            "relative_run_path": (
                f"runs/{row['calibration_id']}/rep_{repetition}/h0"
            ),
            "status": "PENDING",
        }
        for row in selected
        for repetition in (2, 3)
    ]
    jobs_path = out_dir / "r040c_repetition_jobs.jsonl"
    _write_jsonl(jobs_path, jobs)
    summary = {
        "created_at": _now(),
        "status": "FROZEN",
        "screen_count": len(records),
        "screen_outcomes": dict(
            sorted(Counter(row["outcome"] for row in records).items())
        ),
        "qualitative_counts": dict(
            sorted(Counter(row["qualitative_label"] for row in records).items())
        ),
        "candidate_counts": dict(
            sorted(Counter(row["candidate_case"] for row in selected).items())
        ),
        "candidate_sha256": sha256_file(candidate_path),
        "jobs_sha256": sha256_file(jobs_path),
        "job_count": len(jobs),
        "h1_h2_outcomes_read": False,
        "method_evidence": False,
    }
    _write_json(out_dir / "r040c_summary.json", summary)
    return summary


def _stable_case(labels: list[str], expected: str) -> bool:
    counts = Counter(labels)
    if counts["pass"]:
        return expected == "pass" and counts["pass"] >= 2
    return counts[expected] >= 2


def _adaptive_case(labels: list[str], initial_case: str) -> str | None:
    if len(labels) != 3 or any(label == "missing" for label in labels):
        return None
    if initial_case == "pass" and labels == ["pass"] * 3:
        return "stable_pass"
    if initial_case == "closest_failure" and labels == ["closest_failure"] * 3:
        return "stable_closest_failure"
    if (
        initial_case == "stalled"
        and
        not ({"unsafe", "infrastructure_failure"} & set(labels))
        and "pass" in labels
        and bool({"stalled", "closest_failure"} & set(labels))
    ):
        return "unstable"
    return None


def freeze_adaptive_cases(
    candidate_path: Path, runs_dir: Path, out_dir: Path
) -> dict[str, Any]:
    summary_path = candidate_path.parent / "r040c_summary.json"
    if not summary_path.is_file():
        raise ValueError("missing R040C summary")
    source_summary = json.loads(summary_path.read_text())
    if (
        source_summary.get("status") != "FROZEN"
        or source_summary.get("candidate_sha256") != sha256_file(candidate_path)
    ):
        raise ValueError("R040C candidate provenance mismatch")
    candidates = _load_jsonl(candidate_path)
    counts = Counter(row.get("candidate_case") for row in candidates)
    if len(candidates) != 9 or any(counts[case] != 3 for case in CASES):
        raise ValueError("R040C must contain exactly three candidates per initial case")

    audited = []
    for task in candidates:
        repetitions = [
            qualitative_label(
                task,
                runs_dir / task["calibration_id"] / f"rep_{rep}" / "h0",
                rep,
            )
            for rep in (1, 2, 3)
        ]
        labels = [row["qualitative_label"] for row in repetitions]
        audited.append(
            {
                **task,
                "repetitions": repetitions,
                "labels": labels,
                "final_case": _adaptive_case(labels, task["candidate_case"]),
            }
        )
    complete = all(
        row.get("result_available")
        for task in audited
        for row in task["repetitions"]
    )
    frozen = []
    for final_case in FINAL_CASES:
        eligible = [row for row in audited if row["final_case"] == final_case]
        eligible.sort(key=lambda row: (row["selection_rank"], row["calibration_id"]))
        if eligible:
            frozen.append(eligible[0])
    done = complete and len(frozen) == len(FINAL_CASES)

    _require_empty(out_dir)
    audited_path = out_dir / "r040d_adaptive_candidates.jsonl"
    _write_jsonl(audited_path, audited)
    frozen_path = out_dir / "r040d_frozen_cases.json"
    if done:
        _write_json(
            frozen_path,
            {
                "created_at": _now(),
                "status": "FROZEN",
                "adaptive_branch": True,
                "selection_evidence": "h0_only",
                "h1_h2_outcomes_read": False,
                "source_candidate_sha256": sha256_file(candidate_path),
                "criteria": {
                    "stable_pass": "exactly pass/pass/pass",
                    "stable_closest_failure": "exactly closest_failure x3",
                    "unstable": "mixed pass and proof-safe non-pass, with no unsafe/infrastructure/missing",
                },
                "cases": frozen,
            },
        )
    summary = {
        "created_at": _now(),
        "status": "DONE" if done else "INCOMPLETE",
        "adaptive_branch": True,
        "candidate_count": len(candidates),
        "result_count": sum(
            row.get("result_available", False)
            for task in audited
            for row in task["repetitions"]
        ),
        "eligible_counts": dict(
            sorted(Counter(row["final_case"] for row in audited if row["final_case"]).items())
        ),
        "frozen_counts": dict(
            sorted(Counter(row["final_case"] for row in frozen).items())
        ),
        "audited_sha256": sha256_file(audited_path),
        "frozen_sha256": sha256_file(frozen_path) if done else None,
        "h1_h2_outcomes_read": False,
        "evidence_level": "qualitative",
        "method_evidence": False,
    }
    _write_json(out_dir / "r040d_summary.json", summary)
    return summary


def prepare_contrast_manifest(
    frozen_cases_path: Path,
    tasks_path: Path,
    prompts_dir: Path,
    h0_runs_dir: Path,
    out_dir: Path,
) -> dict[str, Any]:
    frozen = json.loads(frozen_cases_path.read_text())
    cases = frozen.get("cases") or []
    if frozen.get("status") != "FROZEN" or {row.get("final_case") for row in cases} != set(FINAL_CASES):
        raise ValueError("adaptive case freeze is incomplete")
    tasks = {row["calibration_id"]: row for row in _load_jsonl(tasks_path)}
    prompt_manifest_path = prompts_dir / "prompt_manifest.json"
    prompt_manifest = json.loads(prompt_manifest_path.read_text())
    if prompt_manifest.get("status") != "FROZEN":
        raise ValueError("prompt manifest is not frozen")
    prompt_paths = {condition: prompts_dir / f"{condition}.txt" for condition in ("h1", "h2")}
    for condition, path in prompt_paths.items():
        if sha256_file(path) != prompt_manifest.get(f"{condition}_sha256"):
            raise ValueError(f"{condition} prompt hash mismatch")

    by_case = {row["final_case"]: row for row in cases}
    records = []
    for final_case in FINAL_CASES:
        task = tasks[by_case[final_case]["calibration_id"]]
        for repetition in (1, 2, 3):
            h0_path = h0_runs_dir / task["calibration_id"] / f"rep_{repetition}" / "h0"
            record = _run_record(task, h0_path, repetition)
            if not record.get("result_available"):
                raise ValueError(f"missing reused H0 result: {task['calibration_id']} rep {repetition}")
            records.append(
                {
                    "job_id": f"{task['calibration_id']}-rep{repetition}-h0",
                    "final_case": final_case,
                    "calibration_id": task["calibration_id"],
                    "selection_rank": task["selection_rank"],
                    "repetition": repetition,
                    "condition": "h0",
                    "status": "REUSED",
                    "run_path": str(h0_path.resolve()),
                    "observed_outcome": record["outcome"],
                }
            )

    sequence = (
        ("stable_pass", 1, "h1"), ("stable_pass", 1, "h2"),
        ("stable_closest_failure", 1, "h2"), ("stable_closest_failure", 1, "h1"),
        ("unstable", 1, "h1"), ("unstable", 1, "h2"),
        ("stable_pass", 2, "h2"), ("stable_pass", 2, "h1"),
        ("stable_closest_failure", 2, "h1"), ("stable_closest_failure", 2, "h2"),
        ("unstable", 2, "h2"), ("unstable", 2, "h1"),
        ("stable_pass", 3, "h1"), ("stable_pass", 3, "h2"),
        ("stable_closest_failure", 3, "h2"), ("stable_closest_failure", 3, "h1"),
        ("unstable", 3, "h1"), ("unstable", 3, "h2"),
    )
    for order, (final_case, repetition, condition) in enumerate(sequence, start=1):
        task = tasks[by_case[final_case]["calibration_id"]]
        records.append(
            {
                "job_id": f"{task['calibration_id']}-rep{repetition}-{condition}",
                "execution_order": order,
                "final_case": final_case,
                "calibration_id": task["calibration_id"],
                "selection_rank": task["selection_rank"],
                "repetition": repetition,
                "condition": condition,
                "status": "PENDING",
                "canonical_source_sha256": task["canonical_source_sha256"],
                "knowledge_sha256": prompt_manifest[f"{condition}_sha256"],
                "relative_run_path": f"runs/{task['calibration_id']}/rep_{repetition}/{condition}",
            }
        )
    if len(records) != 27 or len({row["job_id"] for row in records}) != 27:
        raise AssertionError("contrast manifest must contain 27 unique records")
    _require_empty(out_dir)
    records_path = out_dir / "r041a_contrast_manifest.jsonl"
    _write_jsonl(records_path, records)
    summary = {
        "created_at": _now(),
        "status": "FROZEN",
        "record_count": 27,
        "reused_h0_count": 9,
        "pending_h1_h2_count": 18,
        "frozen_cases_sha256": sha256_file(frozen_cases_path),
        "tasks_sha256": sha256_file(tasks_path),
        "prompt_manifest_sha256": sha256_file(prompt_manifest_path),
        "h1_sha256": prompt_manifest["h1_sha256"],
        "h2_sha256": prompt_manifest["h2_sha256"],
        "records_sha256": sha256_file(records_path),
        "selection_evidence": "h0_only",
        "method_evidence": False,
    }
    _write_json(out_dir / "r041a_contrast_summary.json", summary)
    return summary


def run_contrast_job(
    manifest_path: Path,
    tasks_path: Path,
    corpus_root: Path,
    runs_dir: Path,
    prompts_dir: Path,
    job_id: str,
    model: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    jobs = {row["job_id"]: row for row in _load_jsonl(manifest_path)}
    job = jobs.get(job_id)
    if job is None or job.get("status") != "PENDING":
        raise ValueError(f"unknown or non-pending contrast job: {job_id}")
    condition = job["condition"]
    if condition not in {"h1", "h2"}:
        raise ValueError("contrast runner cannot launch H0")
    knowledge_file = prompts_dir / f"{condition}.txt"
    if sha256_file(knowledge_file) != job["knowledge_sha256"]:
        raise ValueError(f"{condition} knowledge hash mismatch")
    return run_calibration_job(
        tasks_path,
        corpus_root,
        runs_dir,
        job["calibration_id"],
        job["repetition"],
        condition,
        model,
        timeout_seconds,
        knowledge_file=knowledge_file,
    )


def freeze_qualitative_cases(
    candidate_path: Path, runs_dir: Path, out_dir: Path
) -> dict[str, Any]:
    summary_path = candidate_path.parent / "r040c_summary.json"
    if not summary_path.is_file():
        raise ValueError("missing R040C summary")
    source_summary = json.loads(summary_path.read_text())
    if (
        source_summary.get("status") != "FROZEN"
        or source_summary.get("candidate_sha256") != sha256_file(candidate_path)
    ):
        raise ValueError("R040C candidate provenance mismatch")

    candidates = _load_jsonl(candidate_path)
    candidate_counts = Counter(row.get("candidate_case") for row in candidates)
    if len(candidates) != 9 or any(candidate_counts[case] != 3 for case in CASES):
        raise ValueError("R040C must contain exactly three candidates per case")
    audited = []
    for task in candidates:
        records = [
            qualitative_label(
                task,
                runs_dir / task["calibration_id"] / f"rep_{rep}" / "h0",
                rep,
            )
            for rep in (1, 2, 3)
        ]
        audited.append(
            {
                **task,
                "repetitions": records,
                "labels": [row["qualitative_label"] for row in records],
                "stable": _stable_case(
                    [row["qualitative_label"] for row in records],
                    task["candidate_case"],
                ),
            }
        )

    _require_empty(out_dir)
    _write_jsonl(out_dir / "r040d_candidate_repetitions.jsonl", audited)
    complete = all(
        row.get("result_available")
        for task in audited
        for row in task["repetitions"]
    )
    frozen = []
    for case in CASES:
        eligible = [
            row for row in audited if row["candidate_case"] == case and row["stable"]
        ]
        eligible.sort(key=lambda row: (row["selection_rank"], row["calibration_id"]))
        if eligible:
            frozen.append(eligible[0])
    done = complete and len(frozen) == len(CASES)
    summary = {
        "created_at": _now(),
        "status": "DONE" if done else "INCOMPLETE",
        "candidate_count": len(candidates),
        "result_count": sum(
            row.get("result_available", False)
            for task in audited
            for row in task["repetitions"]
        ),
        "stable_counts": dict(
            sorted(Counter(row["candidate_case"] for row in audited if row["stable"]).items())
        ),
        "frozen_counts": dict(
            sorted(Counter(row["candidate_case"] for row in frozen).items())
        ),
        "evidence_level": "qualitative",
        "method_evidence": False,
    }
    _write_json(out_dir / "r040d_summary.json", summary)
    if done:
        _write_json(
            out_dir / "r040d_frozen_cases.json",
            {
                "created_at": _now(),
                "source_candidate_sha256": sha256_file(candidate_path),
                "cases": frozen,
            },
        )
    return summary


def _compact_diff(source: str, verified: str, limit: int) -> str:
    diff = "".join(
        difflib.unified_diff(
            source.splitlines(keepends=True),
            verified.splitlines(keepends=True),
            fromfile="source.rs",
            tofile="verified.rs",
            n=1,
        )
    )
    if len(diff) <= limit:
        return diff
    return diff[:limit] + "\n...[diff excerpt truncated]...\n"


def prepare_distillation_pack(
    selection_path: Path,
    corpus_root: Path,
    out_dir: Path,
    *,
    patch_chars: int = 1800,
    log_chars: int = 900,
) -> dict[str, Any]:
    rows = _load_jsonl(selection_path)
    if len(rows) != 30:
        raise ValueError(f"expected 30 frozen R040 traces, got {len(rows)}")
    corpus_root = corpus_root.resolve()
    packed = []
    for row in rows:
        directory = row.get("directory_group")
        if directory not in ALLOWED_TRACE_DIRECTORIES:
            raise ValueError(f"forbidden distillation directory: {directory}")
        log_path = _resolve_within(
            corpus_root / row["relative_log_path"], corpus_root / directory
        )
        source_path = log_path.with_suffix(".rs")
        verified_path = log_path.with_name(f"{log_path.stem}_verified.rs")
        for path in (log_path, source_path, verified_path):
            if not path.is_file():
                raise ValueError(f"missing trace artifact: {path}")
        if sha256_file(source_path) != row["source"]["sha256"]:
            raise ValueError(f"source hash mismatch: {source_path}")
        if sha256_file(verified_path) != row["verified"]["sha256"]:
            raise ValueError(f"verified hash mismatch: {verified_path}")
        source = source_path.read_text(errors="replace")
        verified = verified_path.read_text(errors="replace")
        log = log_path.read_text(errors="replace")
        packed.append(
            {
                "selection_rank": row["selection_rank"],
                "trace_id": row["trace_id"],
                "directory_group": row["directory_group"],
                "model": row["model"],
                "variant": row["variant"],
                "motifs": row["selection_features"]["motifs"],
                "error_families": row["selection_features"]["error_families"],
                "source_sha256": row["source"]["sha256"],
                "verified_sha256": row["verified"]["sha256"],
                "patch_excerpt": _compact_diff(source, verified, patch_chars),
                "final_log_excerpt": log[-log_chars:],
            }
        )

    _require_empty(out_dir)
    pack_path = out_dir / "r041_distillation_pack.jsonl"
    _write_jsonl(pack_path, packed)
    summary = {
        "created_at": _now(),
        "trace_count": len(packed),
        "selection_sha256": sha256_file(selection_path),
        "pack_sha256": sha256_file(pack_path),
        "patch_chars_per_trace": patch_chars,
        "log_chars_per_trace": log_chars,
        "raw_data_read_only": True,
        "sealed_content_reads": 0,
        "calibration_task_content_reads": 0,
    }
    _write_json(out_dir / "r041_distillation_pack_summary.json", summary)
    return summary


def _token_counter(tokenizer_path: Path):
    try:
        from transformers import AutoTokenizer
    except ImportError as error:
        raise RuntimeError("transformers is required for prompt freezing") from error
    tokenizer = AutoTokenizer.from_pretrained(
        str(tokenizer_path.resolve()), local_files_only=True, trust_remote_code=True
    )
    return lambda text: len(tokenizer.encode(text, add_special_tokens=True))


def _chat_completion(
    endpoint: str,
    model: str,
    system: str,
    user: str,
    *,
    max_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=1800) as response:
        result = json.loads(response.read())
    return payload, result


def _knowledge_text(response: dict[str, Any]) -> str:
    try:
        content = response["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as error:
        raise ValueError("distiller response has no message content") from error
    match = re.search(r"<knowledge>\s*(.*?)\s*</knowledge>", content, re.DOTALL)
    return (match.group(1) if match else content).strip() + "\n"


def generate_h2(
    pack_path: Path,
    tokenizer_path: Path,
    out_dir: Path,
    *,
    endpoint: str = "http://127.0.0.1:8000/v1",
    model: str = "qwen35-27b",
) -> dict[str, Any]:
    output_path = out_dir / "h2_trace_distilled.txt"
    if output_path.exists():
        raise ValueError(f"refusing to overwrite H2: {output_path}")
    pack = pack_path.read_text()
    system = (
        "Distill reusable, global Verus proof-repair knowledge from successful "
        "trajectory evidence. Return only <knowledge>...</knowledge>. The content "
        "must be an actionable ordered protocol, generalize across tasks, avoid "
        "task/function names and copied code, distinguish proof failures from "
        "compile/tool failures, preserve specifications and executable semantics, "
        "and fit within 700 tokenizer tokens."
    )
    user = (
        "The following 30 records contain compact patch and final-log excerpts. "
        "Infer recurring tactics and verification discipline; do not summarize "
        "individual records.\n\n" + pack
    )
    request, response = _chat_completion(
        endpoint, model, system, user, max_tokens=750
    )
    text = _knowledge_text(response)
    tokens = _token_counter(tokenizer_path)(text)
    if tokens > 800:
        raise ValueError(f"H2 exceeds 800-token budget: {tokens}")
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "h2_request.json", request)
    _write_json(out_dir / "h2_response.json", response)
    output_path.write_text(text)
    summary = {
        "created_at": _now(),
        "condition": "h2",
        "model": model,
        "endpoint": endpoint,
        "pack_sha256": sha256_file(pack_path),
        "prompt_sha256": sha256_file(output_path),
        "prompt_tokens": tokens,
        "usage": response.get("usage"),
        "global_prompt": True,
        "task_specific": False,
    }
    _write_json(out_dir / "h2_summary.json", summary)
    return summary


def generate_h1(
    h2_path: Path,
    tokenizer_path: Path,
    out_dir: Path,
    *,
    endpoint: str = "http://127.0.0.1:8000/v1",
    model: str = "qwen35-27b",
) -> dict[str, Any]:
    output_path = out_dir / "h1_generic.txt"
    if output_path.exists():
        raise ValueError(f"refusing to overwrite H1: {output_path}")
    count = _token_counter(tokenizer_path)
    target = count(h2_path.read_text())
    system = (
        "Write a generic Verus proof-repair checklist without using any trace, "
        "dataset, task, patch, or empirical evidence. Return only "
        "<knowledge>...</knowledge>. Keep advice broadly applicable and preserve "
        "specifications and executable semantics."
    )
    initial_user = (
        f"Target approximately {target} tokenizer tokens (acceptable range "
        f"{int(target * 0.95)}-{int(target * 1.05)}). Use an ordered protocol and "
        "avoid task-specific examples."
    )
    attempts = []
    text = ""
    tokens = 0
    for attempt in range(1, 4):
        if attempt == 1:
            user = initial_user
        else:
            direction = "expand" if tokens < target else "shorten"
            user = (
                f"{direction.capitalize()} the generic checklist below to {target} "
                f"tokens, within {int(target * 0.95)}-{int(target * 1.05)} tokens. "
                "Keep it trace-free and return only <knowledge>...</knowledge>.\n\n"
                + text
            )
        request, response = _chat_completion(
            endpoint,
            model,
            system,
            user,
            max_tokens=min(800, max(128, int(target * 1.15))),
        )
        text = _knowledge_text(response)
        tokens = count(text)
        attempts.append(
            {
                "attempt": attempt,
                "request": request,
                "response": response,
                "prompt_tokens": tokens,
            }
        )
        if abs(tokens - target) / target <= 0.05:
            break
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "h1_request.json", request)
    _write_json(out_dir / "h1_response.json", response)
    _write_json(out_dir / "h1_attempts.json", attempts)
    output_path.write_text(text)
    summary = {
        "created_at": _now(),
        "condition": "h1",
        "model": model,
        "endpoint": endpoint,
        "target_tokens": target,
        "prompt_sha256": sha256_file(output_path),
        "prompt_tokens": tokens,
        "length_delta_fraction": abs(tokens - target) / target,
        "generation_attempts": len(attempts),
        "usage": response.get("usage"),
        "trace_evidence_read": False,
        "task_specific": False,
    }
    _write_json(out_dir / "h1_summary.json", summary)
    return summary


def freeze_prompts(
    h1_path: Path,
    h2_path: Path,
    tokenizer_path: Path,
    calibration_tasks: Path,
    r040_selection: Path,
    out_dir: Path,
    pack_path: Path,
    pack_summary_path: Path,
    h1_summary_path: Path,
    h2_summary_path: Path,
    review_record: Path,
) -> dict[str, Any]:
    count = _token_counter(tokenizer_path)
    texts = {"h1": h1_path.read_text(), "h2": h2_path.read_text()}
    tokens = {condition: count(text) for condition, text in texts.items()}
    if tokens["h2"] > 800:
        raise ValueError(f"H2 exceeds 800-token budget: {tokens['h2']}")
    delta = abs(tokens["h1"] - tokens["h2"]) / tokens["h2"]
    if delta > 0.05:
        raise ValueError(f"H1/H2 token delta exceeds 5%: {delta:.3f}")
    forbidden = []
    for path in (calibration_tasks, r040_selection):
        for row in _load_jsonl(path):
            for key in ("task_id", "normalized_task_id", "calibration_id"):
                value = row.get(key)
                if isinstance(value, str) and len(value) >= 8:
                    forbidden.append(value.lower())
    leaks = sorted(
        value
        for value in set(forbidden)
        if value in texts["h1"].lower() or value in texts["h2"].lower()
    )
    if leaks:
        raise ValueError(f"prompt contains frozen task identifiers: {leaks[:3]}")
    permissive_bypass = re.compile(
        r"external_body.{0,40}(?:sparingly|allowed)|"
        r"(?:admit|assume).{0,40}(?:sparingly|allowed)",
        re.IGNORECASE,
    )
    if any(permissive_bypass.search(text) for text in texts.values()):
        raise ValueError("prompt contains permissive proof-bypass advice")
    pack_summary = json.loads(pack_summary_path.read_text())
    h1_summary = json.loads(h1_summary_path.read_text())
    h2_summary = json.loads(h2_summary_path.read_text())
    review = json.loads(review_record.read_text())
    chain_checks = {
        "selection_to_pack": pack_summary.get("selection_sha256")
        == sha256_file(r040_selection),
        "pack_content": pack_summary.get("pack_sha256") == sha256_file(pack_path),
        "pack_to_raw_h2": h2_summary.get("pack_sha256")
        == pack_summary.get("pack_sha256"),
        "raw_h2_to_review": h2_summary.get("prompt_sha256")
        == review.get("h2_raw_sha256"),
        "review_to_frozen_h2": review.get("h2_reviewed_sha256")
        == sha256_file(h2_path),
        "raw_h1_to_review": h1_summary.get("prompt_sha256")
        == review.get("h1_raw_sha256"),
        "review_to_frozen_h1": review.get("h1_reviewed_sha256")
        == sha256_file(h1_path),
        "h1_trace_free_generation": h1_summary.get("trace_evidence_read") is False,
        "review_safety": review.get("safety_verdict") == "PASS",
    }
    failed_checks = [name for name, passed in chain_checks.items() if not passed]
    if failed_checks:
        raise ValueError(f"prompt provenance chain failed: {failed_checks}")

    _require_empty(out_dir)
    frozen_paths = {}
    for condition, source in (("h1", h1_path), ("h2", h2_path)):
        target = out_dir / f"{condition}.txt"
        target.write_text(source.read_text())
        frozen_paths[condition] = target
    manifest = {
        "created_at": _now(),
        "status": "FROZEN",
        "h1_sha256": sha256_file(frozen_paths["h1"]),
        "h2_sha256": sha256_file(frozen_paths["h2"]),
        "h1_tokens": tokens["h1"],
        "h2_tokens": tokens["h2"],
        "token_delta_fraction": delta,
        "tokenizer_config_sha256": sha256_file(tokenizer_path / "tokenizer_config.json"),
        "model_config_sha256": sha256_file(tokenizer_path / "config.json"),
        "calibration_tasks_sha256": sha256_file(calibration_tasks),
        "r040_selection_sha256": sha256_file(r040_selection),
        "distillation_pack_sha256": sha256_file(pack_path),
        "pack_summary_sha256": sha256_file(pack_summary_path),
        "h1_generation_summary_sha256": sha256_file(h1_summary_path),
        "h2_generation_summary_sha256": sha256_file(h2_summary_path),
        "global_h2": True,
        "task_specific": False,
        "task_identifier_leaks": [],
        "permissive_bypass_advice": False,
        "review_record_sha256": sha256_file(review_record),
        "reviewer_type": review.get("reviewer_type"),
        "agent_edit_minutes": review.get("agent_edit_minutes"),
        "human_edit_minutes": review.get("human_edit_minutes"),
        "provenance_chain": chain_checks,
        "method_evidence": False,
    }
    _write_json(out_dir / "prompt_manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(prog="handsoff-rationale")
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select-candidates")
    select.add_argument("--tasks", type=Path, required=True)
    select.add_argument("--runs-dir", type=Path, required=True)
    select.add_argument("--out-dir", type=Path, required=True)
    select.add_argument("--per-case", type=int, default=3)
    freeze = commands.add_parser("freeze-cases")
    freeze.add_argument("--candidates", type=Path, required=True)
    freeze.add_argument("--runs-dir", type=Path, required=True)
    freeze.add_argument("--out-dir", type=Path, required=True)
    adaptive = commands.add_parser("freeze-adaptive-cases")
    adaptive.add_argument("--candidates", type=Path, required=True)
    adaptive.add_argument("--runs-dir", type=Path, required=True)
    adaptive.add_argument("--out-dir", type=Path, required=True)
    contrast = commands.add_parser("prepare-contrast")
    contrast.add_argument("--frozen-cases", type=Path, required=True)
    contrast.add_argument("--tasks", type=Path, required=True)
    contrast.add_argument("--prompts-dir", type=Path, required=True)
    contrast.add_argument("--h0-runs-dir", type=Path, required=True)
    contrast.add_argument("--out-dir", type=Path, required=True)
    contrast_job = commands.add_parser("run-contrast-job")
    contrast_job.add_argument("--manifest", type=Path, required=True)
    contrast_job.add_argument("--tasks", type=Path, required=True)
    contrast_job.add_argument("--corpus-root", type=Path, required=True)
    contrast_job.add_argument("--runs-dir", type=Path, required=True)
    contrast_job.add_argument("--prompts-dir", type=Path, required=True)
    contrast_job.add_argument("--job-id", required=True)
    contrast_job.add_argument("--model", default="qwen35-27b")
    contrast_job.add_argument("--timeout-seconds", type=int, default=1200)
    pack = commands.add_parser("prepare-distillation-pack")
    pack.add_argument("--selection", type=Path, required=True)
    pack.add_argument("--corpus-root", type=Path, required=True)
    pack.add_argument("--out-dir", type=Path, required=True)
    h2 = commands.add_parser("generate-h2")
    h2.add_argument("--pack", type=Path, required=True)
    h2.add_argument("--tokenizer-path", type=Path, required=True)
    h2.add_argument("--out-dir", type=Path, required=True)
    h2.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    h2.add_argument("--model", default="qwen35-27b")
    h1 = commands.add_parser("generate-h1")
    h1.add_argument("--h2", type=Path, required=True)
    h1.add_argument("--tokenizer-path", type=Path, required=True)
    h1.add_argument("--out-dir", type=Path, required=True)
    h1.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    h1.add_argument("--model", default="qwen35-27b")
    freeze_prompts_parser = commands.add_parser("freeze-prompts")
    freeze_prompts_parser.add_argument("--h1", type=Path, required=True)
    freeze_prompts_parser.add_argument("--h2", type=Path, required=True)
    freeze_prompts_parser.add_argument("--tokenizer-path", type=Path, required=True)
    freeze_prompts_parser.add_argument("--calibration-tasks", type=Path, required=True)
    freeze_prompts_parser.add_argument("--r040-selection", type=Path, required=True)
    freeze_prompts_parser.add_argument("--out-dir", type=Path, required=True)
    freeze_prompts_parser.add_argument("--pack", type=Path, required=True)
    freeze_prompts_parser.add_argument("--pack-summary", type=Path, required=True)
    freeze_prompts_parser.add_argument("--h1-summary", type=Path, required=True)
    freeze_prompts_parser.add_argument("--h2-summary", type=Path, required=True)
    freeze_prompts_parser.add_argument("--review-record", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "select-candidates":
        result = select_qualitative_candidates(
            args.tasks,
            args.runs_dir,
            validate_output_path(args.out_dir),
            per_case=args.per_case,
        )
    elif args.command == "freeze-cases":
        result = freeze_qualitative_cases(
            args.candidates, args.runs_dir, validate_output_path(args.out_dir)
        )
    elif args.command == "freeze-adaptive-cases":
        result = freeze_adaptive_cases(
            args.candidates, args.runs_dir, validate_output_path(args.out_dir)
        )
    elif args.command == "prepare-contrast":
        result = prepare_contrast_manifest(
            args.frozen_cases,
            args.tasks,
            args.prompts_dir,
            args.h0_runs_dir,
            validate_output_path(args.out_dir),
        )
    elif args.command == "run-contrast-job":
        result = run_contrast_job(
            args.manifest,
            args.tasks,
            args.corpus_root,
            validate_output_path(args.runs_dir, data_root=args.corpus_root),
            args.prompts_dir,
            args.job_id,
            args.model,
            args.timeout_seconds,
        )
    elif args.command == "prepare-distillation-pack":
        result = prepare_distillation_pack(
            args.selection,
            args.corpus_root,
            validate_output_path(args.out_dir, data_root=args.corpus_root),
        )
    elif args.command == "generate-h2":
        result = generate_h2(
            args.pack,
            args.tokenizer_path,
            validate_output_path(args.out_dir),
            endpoint=args.endpoint,
            model=args.model,
        )
    elif args.command == "generate-h1":
        result = generate_h1(
            args.h2,
            args.tokenizer_path,
            validate_output_path(args.out_dir),
            endpoint=args.endpoint,
            model=args.model,
        )
    else:
        result = freeze_prompts(
            args.h1,
            args.h2,
            args.tokenizer_path,
            args.calibration_tasks,
            args.r040_selection,
            validate_output_path(args.out_dir),
            args.pack,
            args.pack_summary,
            args.h1_summary,
            args.h2_summary,
            args.review_record,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

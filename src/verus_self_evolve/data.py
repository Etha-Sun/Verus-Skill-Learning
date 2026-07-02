from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .models import Attempt, Trace


ATTEMPT_RE = re.compile(r"Repair attempt\s+(\d+)/(\d+)")
TARGET_RE = re.compile(r"Target error:\s*(?:VerusErrorType\.)?([A-Za-z0-9_]+)")
ACTION_RE = re.compile(r"['\"]primary_action['\"]:\s*['\"]([^'\"]+)['\"]")
INPUT_RE = re.compile(r"Input tokens:\s*(\d+)")
OUTPUT_RE = re.compile(r"Output tokens:\s*(\d+)")
LEMMA_RE = re.compile(r"Lemmas found:\s*\d+\s*-\s*\[(.*?)\]")
RECURSIVE_RE = re.compile(r"Recursive functions found:\s*\d+\s*-\s*\[(.*?)\]")
OPAQUE_RE = re.compile(r"Opaque functions found:\s*\d+\s*-\s*\[(.*?)\]")
TIME_SUFFIX_RE = re.compile(r"-\d{8}-\d{6}$")


def model_from_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("all_batch_results-cyy-"):
            return part.removeprefix("all_batch_results-cyy-")
    return "unknown"


def batch_from_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("results-batch_"):
            return part
    return "unknown"


def file_from_output_dir(path: Path) -> str:
    name = path.name
    if name.startswith("o-"):
        name = name[2:]
    name = TIME_SUFFIX_RE.sub("", name)
    return f"{name}.rs"


def project_from_file(file_name: str) -> str:
    return file_name.split("__", 1)[0]


def parse_list_field(text: str, regex: re.Pattern[str]) -> tuple[str, ...]:
    match = regex.search(text)
    if not match:
        return ()
    values = []
    for item in match.group(1).split(","):
        item = item.strip().strip("'\"")
        if item:
            values.append(item)
    return tuple(values)


def parse_attempts(text: str) -> tuple[Attempt, ...]:
    matches = list(ATTEMPT_RE.finditer(text))
    attempts = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end]
        target_match = TARGET_RE.search(chunk)
        action_match = ACTION_RE.search(chunk)
        input_tokens = sum(int(x) for x in INPUT_RE.findall(chunk))
        output_tokens = sum(int(x) for x in OUTPUT_RE.findall(chunk))
        accepted = (
            "Action accepted" in chunk
            or "Candidate 1 accepted" in chunk
            or "is the new best candidate" in chunk
        )
        attempts.append(
            Attempt(
                index=int(match.group(1)),
                target_error=target_match.group(1) if target_match else "",
                action=action_match.group(1) if action_match else "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                accepted=accepted,
            )
        )
    return tuple(attempts)


def _to_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def _to_float(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def read_result_rows(data_root: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    rows: dict[tuple[str, str, str], dict[str, str]] = {}
    for result_csv in data_root.glob("all_batch_results-cyy-*/results-batch_*/results.csv"):
        model = model_from_path(result_csv)
        batch = batch_from_path(result_csv)
        with result_csv.open(newline="", errors="replace") as f:
            for row in csv.DictReader(f):
                file_name = row.get("file", "")
                if file_name:
                    rows[(model, batch, file_name)] = row
    return rows


def load_traces(data_root: Path) -> list[Trace]:
    result_rows = read_result_rows(data_root)
    traces: list[Trace] = []
    for log_path in data_root.glob("all_batch_results-cyy-*/results-batch_*/o-*/verus-repair.log"):
        model = model_from_path(log_path)
        batch = batch_from_path(log_path)
        file_name = file_from_output_dir(log_path.parent)
        result = result_rows.get((model, batch, file_name))
        if result is None:
            continue
        text = log_path.read_text(errors="replace")
        traces.append(
            Trace(
                model=model,
                batch=batch,
                project=project_from_file(file_name),
                file=file_name,
                status=result.get("status", ""),
                csv_total_tokens=_to_int(result.get("total_tokens")),
                time_seconds=_to_float(result.get("time_seconds")),
                lemmas=parse_list_field(text, LEMMA_RE),
                recursive_functions=parse_list_field(text, RECURSIVE_RE),
                opaque_functions=parse_list_field(text, OPAQUE_RE),
                attempts=parse_attempts(text),
                log_path=str(log_path),
            )
        )
    return traces


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_data_manifest(data_root: Path, out_path: Path, traces: list[Trace]) -> None:
    result_csvs = sorted(data_root.glob("all_batch_results-cyy-*/results-batch_*/results.csv"))
    status_counts = Counter(trace.status for trace in traces)
    manifest = {
        "data_root": str(data_root.resolve()),
        "scope": "all_batch_results-cyy-*/results-batch_*/ only",
        "read_only_contract": True,
        "result_csv_count": len(result_csvs),
        "trace_count": len(traces),
        "status_counts": dict(sorted(status_counts.items())),
        "result_csv_sha256": {str(path): sha256_file(path) for path in result_csvs},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


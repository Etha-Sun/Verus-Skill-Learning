#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verus_self_evolve.proof_progress import (
    align_tool_calls_to_output_tokens,
    extract_verifier_calls,
    function_body,
    greedy_prune_proof_lines,
    load_jsonl,
    proof_line_coverage,
)
from verus_self_evolve.trajectory_progress import verifier_state


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: list[str], timeout_seconds: int) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    output = f"{completed.stdout}{completed.stderr}"
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
        "verifier": verifier_state(output),
    }


def _write_log(path: Path, result: dict[str, Any]) -> None:
    path.write_text(
        f"command: {json.dumps(result['command'])}\n"
        f"returncode: {result['returncode']}\n"
        f"stdout:\n{result['stdout']}\n"
        f"stderr:\n{result['stderr']}\n",
        encoding="utf-8",
    )


def _ledger_records(ledger_path: Path, task_id: str) -> list[dict[str, Any]]:
    records = [
        row
        for row in load_jsonl(ledger_path)
        if task_id in str(row.get("task_id") or "")
    ]
    if not records:
        raise ValueError(f"no ledger records found for task {task_id}")
    return records


def _snapshot_sources(prediction_dir: Path) -> dict[str, tuple[str, str]]:
    sources: dict[str, tuple[str, str]] = {}
    for path in sorted((prediction_dir / "snapshots").glob("*-candidate.rs")):
        sources.setdefault(
            _sha256(path),
            (
                path.read_text(encoding="utf-8", errors="replace"),
                path.relative_to(prediction_dir).as_posix(),
            ),
        )
    return sources


def _stagnation_segments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stagnant_edges = []
    for left, right in zip(rows, rows[1:]):
        token_delta = right["cumulative_output_tokens"] - left["cumulative_output_tokens"]
        same_coverage = abs(right["proof_coverage"] - left["proof_coverage"]) < 1e-12
        same_tier = right["verifier_tier"] == left["verifier_tier"]
        still_searching = left["verifier_tier"] < 2
        if token_delta > 0 and same_coverage and same_tier and still_searching:
            stagnant_edges.append((left, right))
    segments = []
    for left, right in stagnant_edges:
        if segments and segments[-1]["end_call"] == left["call_ordinal"]:
            segments[-1]["end_call"] = right["call_ordinal"]
            segments[-1]["end_output_tokens"] = right["cumulative_output_tokens"]
            segments[-1]["output_token_delta"] = (
                segments[-1]["end_output_tokens"]
                - segments[-1]["start_output_tokens"]
            )
        else:
            segments.append(
                {
                    "start_call": left["call_ordinal"],
                    "end_call": right["call_ordinal"],
                    "start_output_tokens": left["cumulative_output_tokens"],
                    "end_output_tokens": right["cumulative_output_tokens"],
                    "output_token_delta": right["cumulative_output_tokens"]
                    - left["cumulative_output_tokens"],
                    "proof_coverage": left["proof_coverage"],
                    "verifier_tier": left["verifier_tier"],
                }
            )
    return segments


def _regression_transitions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transitions = []
    for left, right in zip(rows, rows[1:]):
        coverage_delta = right["proof_coverage"] - left["proof_coverage"]
        tier_delta = right["verifier_tier"] - left["verifier_tier"]
        if coverage_delta >= 0 and tier_delta >= 0:
            continue
        transitions.append(
            {
                "from_call": left["call_ordinal"],
                "to_call": right["call_ordinal"],
                "from_output_tokens": left["cumulative_output_tokens"],
                "to_output_tokens": right["cumulative_output_tokens"],
                "coverage_delta": coverage_delta,
                "verifier_tier_delta": tier_delta,
            }
        )
    return transitions


def _write_calls_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "call_ordinal",
        "event_index",
        "origin",
        "tool_call_id",
        "candidate_sha256",
        "source_snapshot",
        "exported_state",
        "cumulative_output_tokens",
        "verifier_tier_name",
        "verifier_tier",
        "matched_final_lines",
        "pruned_final_lines",
        "proof_coverage",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in columns} for row in rows)


def _write_removed_lines_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "original_line_number",
        "category",
        "unit_kind",
        "pass_ordinal",
        "line",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in columns} for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction-dir", type=Path, required=True)
    parser.add_argument("--function-name", required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--lynette-bin", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    args = parser.parse_args()

    prediction_dir = args.prediction_dir.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir == prediction_dir or prediction_dir in output_dir.parents:
        raise ValueError("output directory must be outside the raw prediction directory")
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite existing output: {output_dir}")
    output_dir.mkdir(parents=True)

    result_path = prediction_dir / "result.json"
    events_path = prediction_dir / "agent_events.jsonl"
    input_path = prediction_dir / "workspace/input.rs"
    final_path = prediction_dir / "workspace/candidate.rs"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    task_id = str(result.get("id") or prediction_dir.name)
    ledger_path = prediction_dir.parent.parent / "bridge_calls.jsonl"
    events = load_jsonl(events_path)
    ledger = _ledger_records(ledger_path, task_id)
    baseline_source = input_path.read_text(encoding="utf-8", errors="replace")
    final_source = final_path.read_text(encoding="utf-8", errors="replace")

    original_validation = _run(
        [str(args.verus_bin.resolve()), str(final_path)], args.timeout_seconds
    )
    _write_log(output_dir / "verus_original.log", original_validation)
    if not original_validation["passed"] or original_validation["verifier"]["tier_rank"] != 2:
        raise RuntimeError("the original final candidate does not pass Verus")

    with tempfile.TemporaryDirectory(prefix="verus-proof-prune-") as temporary:
        trial_path = Path(temporary) / "candidate.rs"

        def verify_trial(source: str) -> tuple[bool, str]:
            trial_path.write_text(source, encoding="utf-8")
            trial = _run(
                [str(args.verus_bin.resolve()), str(trial_path)], args.timeout_seconds
            )
            passed = trial["passed"] and trial["verifier"]["tier_rank"] == 2
            return passed, f"{trial['stdout']}{trial['stderr']}"

        pruning = greedy_prune_proof_lines(
            baseline_source,
            final_source,
            args.function_name,
            verify_trial,
        )

    pruned_path = output_dir / "pruned_candidate.rs"
    pruned_path.write_text(pruning["pruned_source"], encoding="utf-8")
    with (output_dir / "pruning_trials.jsonl").open("w", encoding="utf-8") as handle:
        for row in pruning["trials"]:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    _write_removed_lines_csv(
        output_dir / "removed_lines.csv", pruning["removed_line_records"]
    )

    pruned_verus = _run(
        [str(args.verus_bin.resolve()), str(pruned_path)], args.timeout_seconds
    )
    pruned_lynette = _run(
        [
            str(args.lynette_bin.resolve()),
            "compare",
            "-t",
            str(input_path),
            str(pruned_path),
        ],
        args.timeout_seconds,
    )
    _write_log(output_dir / "verus_pruned.log", pruned_verus)
    _write_log(output_dir / "lynette_pruned.log", pruned_lynette)
    if not pruned_verus["passed"] or pruned_verus["verifier"]["tier_rank"] != 2:
        raise RuntimeError("the pruned candidate does not pass Verus")
    if not pruned_lynette["passed"]:
        raise RuntimeError("the pruned candidate does not pass Lynette")

    alignment = align_tool_calls_to_output_tokens(events, ledger)
    snapshots = _snapshot_sources(prediction_dir)
    calls = extract_verifier_calls(events)
    pruned_body = function_body(pruning["pruned_source"], args.function_name)
    call_rows = []
    state_dir = output_dir / "verifier_call_states"
    state_dir.mkdir()
    for call in calls:
        digest = call.get("candidate_sha256")
        if digest not in snapshots:
            raise ValueError(f"verifier call has no exact snapshot: {digest}")
        source, source_path = snapshots[digest]
        coverage = proof_line_coverage(
            function_body(source, args.function_name), pruned_body
        )
        if call["origin"] == "actor":
            output_tokens = alignment["tool_call_output_tokens"].get(call["tool_call_id"])
            if output_tokens is None:
                raise ValueError(f"verifier call has no output-token alignment: {call}")
        else:
            output_tokens = alignment["total_output_tokens"]
        state_name = (
            f"call_{call['call_ordinal']:02d}_event_{int(call['event_index']):03d}_"
            f"tier_{call['verifier']['tier_rank']}.rs"
        )
        (state_dir / state_name).write_text(source, encoding="utf-8")
        call_rows.append(
            {
                **call,
                "source_snapshot": source_path,
                "exported_state": f"verifier_call_states/{state_name}",
                "cumulative_output_tokens": output_tokens,
                "verifier_tier_name": call["verifier"]["tier"],
                "verifier_tier": call["verifier"]["tier_rank"],
                "matched_final_lines": coverage["matched_final_lines"],
                "pruned_final_lines": coverage["final_lines"],
                "proof_coverage": coverage["coverage"],
            }
        )
    _write_calls_csv(output_dir / "verifier_calls.csv", call_rows)

    first_verified_index = next(
        (
            index
            for index, row in enumerate(call_rows)
            if row["verifier_tier"] == 2
        ),
        None,
    )
    first_verified_tokens = (
        call_rows[first_verified_index]["cumulative_output_tokens"]
        if first_verified_index is not None
        else None
    )

    summary = {
        "schema_version": "verus-call-proof-coverage-v1",
        "task_id": task_id,
        "function_name": args.function_name,
        "hindsight_only": True,
        "raw_data_read_only": True,
        "x_axis": "cumulative complete-ledger completion_tokens",
        "y_axis": "normalized target-proof line coverage of verifier-pruned final proof",
        "verifier_call_count": len(call_rows),
        "unique_candidate_count": len({row["candidate_sha256"] for row in call_rows}),
        "repeated_candidate_call_count": len(call_rows)
        - len({row["candidate_sha256"] for row in call_rows}),
        "total_output_tokens": alignment["total_output_tokens"],
        "token_alignment": alignment,
        "pruning": pruning["summary"],
        "removed_line_categories": dict(
            sorted(
                Counter(
                    row["category"] for row in pruning["removed_line_records"]
                ).items()
            )
        ),
        "stagnation_segments": _stagnation_segments(call_rows),
        "regression_transitions": _regression_transitions(call_rows),
        "post_first_verified": {
            "additional_verifier_calls": (
                len(call_rows) - first_verified_index - 1
                if first_verified_index is not None
                else 0
            ),
            "additional_output_tokens": (
                alignment["total_output_tokens"] - first_verified_tokens
                if first_verified_tokens is not None
                else 0
            ),
            "first_verified_call": (
                call_rows[first_verified_index]["call_ordinal"]
                if first_verified_index is not None
                else None
            ),
            "first_verified_output_tokens": first_verified_tokens,
        },
        "validation": {
            "original_verus_passed": original_validation["passed"],
            "pruned_verus_passed": pruned_verus["passed"],
            "pruned_lynette_passed": pruned_lynette["passed"],
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = {
        "schema_version": "verus-call-proof-coverage-run-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "python": sys.version,
        "platform": platform.platform(),
        "analysis_script_sha256": _sha256(Path(__file__).resolve()),
        "proof_progress_module_sha256": _sha256(
            Path(__file__).resolve().parents[1]
            / "src/verus_self_evolve/proof_progress.py"
        ),
        "prediction_dir": str(prediction_dir),
        "input_sha256": _sha256(input_path),
        "original_final_sha256": _sha256(final_path),
        "pruned_final_sha256": _sha256(pruned_path),
        "events_sha256": _sha256(events_path),
        "ledger_sha256": _sha256(ledger_path),
        "verus_bin": str(args.verus_bin.resolve()),
        "verus_sha256": _sha256(args.verus_bin.resolve()),
        "lynette_bin": str(args.lynette_bin.resolve()),
        "lynette_sha256": _sha256(args.lynette_bin.resolve()),
        "outputs": sorted(path.name for path in output_dir.iterdir()),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

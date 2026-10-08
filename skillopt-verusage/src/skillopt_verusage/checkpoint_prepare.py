"""Offline train-only checkpoint preparation. Never invokes a model or actor."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

from skillopt_verusage.campaign_evidence import load_trace, sha
from skillopt_verusage.checkpoint_selection import POLICIES, select_checkpoints
from skillopt_verusage.guarded_deepseek import write_json
from verus_self_evolve.proof_progress import align_tool_calls_to_output_tokens, extract_verifier_calls


def prepare(manifest, source_root, reviewed_root, output_root, *, policy="rule_based_v1", lynette_bin=None,
            included_ids=None):
    approved = Path(os.environ["VERUS_SKILL_RUN_ROOT"]).resolve()
    output_root = Path(output_root).resolve()
    source_root, reviewed_root = Path(source_root).resolve(), Path(reviewed_root).resolve()
    if (approved not in output_root.parents or output_root.exists()
            or source_root in output_root.parents or reviewed_root in output_root.parents):
        raise ValueError("Preparation requires a fresh external run-root child")
    if sha(Path(manifest)) != "0e42aad8c5e8a6789d06e7b15cfdca903479b16dc76f863544f219e6bbe40536":
        raise ValueError("Only the unchanged fixed train-40 manifest is admitted")
    items = json.loads(Path(manifest).read_text())
    provenance_path = reviewed_root/"report_provenance.json"
    provenance = json.loads(provenance_path.read_text())["reports"]
    reports = {r["id"]: r for r in provenance}
    if len(items) != 40 or len(reports) != 39 or len(reports) != len(provenance):
        raise ValueError("Expected 40 originals and 39 distinct reviewed reference reports")
    if included_ids is not None:
        included_ids = list(included_ids)
        if (not included_ids or len(set(included_ids)) != len(included_ids)
                or not set(included_ids) <= {item['id'] for item in items}):
            raise ValueError("Learning subset must contain distinct fixed-train identifiers")
        items = [item for item in items if item['id'] in included_ids]
    ledger_path = source_root/"bridge_calls.jsonl"
    ledger = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    selections, jobs = {}, []
    for item in items:
        ident = item["id"]
        directory = source_root/"rollout/predictions"/ident
        trace, _, snapshots = load_trace(directory)
        result = trace["result"]
        if (result.get("fidelity") == "V0_INVALID" or result.get("source_sha256") != item["source_sha256"]
                or result.get("actor_model") != "deepseek-v4-pro"
                or result.get("actor_reasoning_effort") != "max"):
            raise ValueError("Unaccepted original actor/source contract: " + ident)
        if sha(directory/"workspace/input.rs") != item["source_sha256"]:
            raise ValueError("Original input hash mismatch: " + ident)
        if ident in reports:
            binding = reports[ident]
            path = Path(binding["report_path"])
            if sha(path) != binding["report_sha256"]:
                raise ValueError("Reviewed report hash mismatch: " + ident)
            report = json.loads(path.read_text())
            if (not result["hard"] or report["id"] != ident
                    or report["source_events_sha256"] != sha(directory/"agent_events.jsonl")):
                raise ValueError("Reviewed report source binding mismatch: " + ident)
            report_binding = binding
        else:
            if result["hard"]:
                raise ValueError("Verified original omitted from reviewed reports: " + ident)
            calls = extract_verifier_calls(trace["events"])
            alignment = align_tool_calls_to_output_tokens(trace["events"],
                          [row for row in ledger if row.get("task_id") == result["bridge_task_key"]])
            curve = [{**call, "verifier_tier": call["verifier"]["tier_rank"],
                      "cumulative_output_tokens": alignment["tool_call_output_tokens"][call["tool_call_id"]]
                      if call["origin"] == "actor" else alignment["total_output_tokens"]}
                     for call in calls]
            report = {"function_name": item["task_id"].split("__")[-1], "curve": curve,
                      "reference_kind": "no_verified_reference"}
            report_binding = {"reference_kind": "no_verified_reference",
                              "source_events_sha256": sha(directory/"agent_events.jsonl")}
        admission = {}
        def allowed(point):
            code_hash = point["checkpoint_sha256"]
            if code_hash not in admission:
                work = output_root/"preservation"/ident
                work.mkdir(parents=True, exist_ok=True)
                baseline, candidate = work/"input.rs", work/(code_hash+".rs")
                baseline.write_text(trace["original_input"])
                candidate.write_text(snapshots[code_hash])
                try:
                    check = subprocess.run([str(lynette_bin), "compare", "-t", str(baseline), str(candidate)],
                                           capture_output=True, text=True, timeout=30, check=False)
                    admission[code_hash] = {"passed": check.returncode == 0,
                                            "output": check.stdout+check.stderr, "returncode": check.returncode}
                except subprocess.TimeoutExpired:
                    admission[code_hash] = {"passed": False, "timeout": True}
                write_json(work/"audit.json", admission)
            return admission[code_hash]["passed"]
        selection = select_checkpoints(report, trace, snapshots, policy=policy,
                                       checkpoint_allowed=allowed if lynette_bin else None)
        selection.update(source_task=ident, report_binding=report_binding,
                         source_result_sha256=sha(directory/"result.json"),
                         preservation_checked=lynette_bin is not None)
        selections[ident] = selection
        for point in selection["selected"]:
            jobs.append({"source_task": ident, "checkpoint": point,
                         "source_sha256": item["source_sha256"], "model": "deepseek-v4-pro",
                         "reasoning_effort": "max", "timeout_seconds": 1800,
                         "context_mode": "checkpoint_code_plus_visible_prefix_rehydration",
                         "branch_directory": f"augmentation/{ident}/{point['checkpoint_id']}"})
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root/"selections.json", selections)
    write_json(output_root/"fork_jobs.json", jobs)
    write_json(output_root/"manifest.json", {"schema_version": "checkpoint-preparation-v1",
        "train_manifest_sha256": sha(Path(manifest)), "report_provenance_sha256": sha(provenance_path),
        "source_ledger_sha256": sha(ledger_path), "policy": policy, "source_tasks": len(selections),
        "included_ids": [item['id'] for item in items],
        "checkpoints": len(jobs), "preservation_checked": lynette_bin is not None,
        "paid_requests": 0, "test_accessed": False,
        "raw_inputs_modified": False, "selections_sha256": sha(output_root/"selections.json")})
    return selections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "source-root", "reviewed-root", "output-root"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--policy", choices=POLICIES, default="rule_based_v1")
    parser.add_argument("--lynette-bin", type=Path, required=True)
    args = parser.parse_args()
    selections = prepare(args.manifest, args.source_root, args.reviewed_root, args.output_root,
                         policy=args.policy, lynette_bin=args.lynette_bin)
    print(json.dumps({"sources": len(selections), "checkpoints": sum(len(s['selected']) for s in selections.values()),
                      "paid_requests": 0, "output": str(args.output_root)}))


if __name__ == "__main__":
    main()

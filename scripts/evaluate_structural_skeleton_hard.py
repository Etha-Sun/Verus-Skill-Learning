"""Run the reviewed harder development pilot without altering the old pilot."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import fcntl
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

import evaluate_card_organization as prior
from continue_card_organization_evaluation import result_dimensions
from skill_evolution_pilot.codex_runner import build_prompt
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import BudgetMux, write_json
from skillopt_verusage.skill_artifact import load_skill_artifact


REPO = Path(__file__).resolve().parents[1]
ARMS = ("p0", "p1", "p2")
CASES = (
    {"task": "a23a4969155913255f76", "packet": "temporal-transfer", "label": "Rely equivalence"},
    {"task": "9b9f6ccef89db4103c7f", "packet": "temporal-transfer", "label": "Unpack conditions"},
    {"task": "aded79905be896942897", "packet": "semantic-equality", "label": "Temporal De Morgan"},
)
AUTHORIZATION = {
    "episodes": 18, "repeats": 2, "budget_usd": 10, "timeout_seconds": 600,
    "primary": "historical budgeted_dual_pass and strict V2, unchanged",
    "secondary": "observed same-hash Verus and Lynette completions within 600s",
    "basis": "User explicitly selected 18 episodes/USD10 and unchanged primary plus separate deadline-dual report; server background launch authorized.",
}


def schedule(root):
    jobs = []
    for repeat in range(2):
        for position, case in enumerate(CASES):
            offset = (position + repeat) % len(ARMS)
            order = ARMS[offset:] + ARMS[:offset]
            if repeat:
                order = tuple(reversed(order))
            for arm in order:
                job = {"id": case["task"], "condition": arm, "repeat": repeat}
                if arm != "p0":
                    job["knowledge_path"] = str(root / "packets" / case["packet"] / (arm + ".md"))
                jobs.append(job)
    return jobs


def expected_prompt(root, job):
    prompt = (root / "TASK.md").read_text()
    if "knowledge_path" in job:
        prompt += "\n\n" + Path(job["knowledge_path"]).read_text().strip() + "\n"
    return prompt


def prepare(root, preparation, config_path):
    prior.require(not root.exists(), "Fresh output root required")
    verified = subprocess.run(["python3", str(preparation / "check_preparation.py")],
                              capture_output=True, text=True, timeout=60)
    prior.require(verified.returncode == 0, "Material preparation checks failed: " + verified.stderr)
    config = prior.read(config_path)
    config["repo"] = str(REPO)
    prior.require(Path(config["env_file"]).resolve() == REPO.parent / "Trace2Skill/.env.deepseek", "Wrong credentials path")
    for key in ("codex_bin", "lynette_bin"):
        prior.require(prior.driver.sha(config[key]) == prior.HISTORICAL[key], "Tool changed: " + key)
    prior.require(prior.driver.sha(config["catalog"]) == prior.HISTORICAL["models.json"], "Model catalog changed")
    verus_root = Path(config["verus_bin"]).parent
    prior.require(prior.driver.sha(verus_root / "rust_verify") == prior.LOCAL_RUST_VERIFY, "Verifier changed")
    root.mkdir(parents=True)
    (root / "executive").mkdir()
    shutil.copyfile(preparation / "common/SKILL.md", root / "executive/SKILL.md")
    shutil.copyfile(preparation / "common/TASK.md", root / "TASK.md")
    prior.require((root / "TASK.md").read_text() == build_prompt(installed_library_root=verus_root / "vstd"), "TASK changed")
    shutil.copytree(preparation / "packets", root / "packets")
    (root / "runtime").mkdir()
    shutil.copyfile(config["catalog"], root / "runtime/models.json")
    config["source_root"] = str(root / "runtime")
    write_json(root / "config.json", config)
    write_json(root / "authorization.json", AUTHORIZATION)
    contract = prior.driver.prepare(root / "config.json", root / "executive", root / "executive", root,
                                    task_ids=tuple(case["task"] for case in CASES),
                                    installed_library_conditions=("old", "revised"))
    artifact = load_skill_artifact(root / "executive").manifest()
    contract.update(schema_version="structural-skeleton-hard-v1", expected_episodes=18, repeats=2, budget_usd=10,
                    artifacts={arm: artifact for arm in ARMS}, bundle_paths={arm: str(root / "executive") for arm in ARMS},
                    installed_library_conditions=list(ARMS), schedule=schedule(root), cases=list(CASES),
                    model_context_window=1048576, max_output_tokens_per_request=131072,
                    provider_request_timeout_seconds=1800, transport_retry=False,
                    preparation_root=str(preparation), authorization=AUTHORIZATION,
                    expense_policy="Fresh USD10 total including failed/unknown requests, conservative reservations, no retries.",
                    environment_deviation="Same previously authorized local Verus, different hash from Yuechun historical build.",
                    caveat="Three selected validation development tasks, two repeats; fixed exposure, no bank. Second-style unresolved structures, not worked examples. Two independent train tasks; De Morgan coverage is partial. No unseen generalization claim.")
    for path, receipt in prior.read(preparation / "material_manifest.json").items():
        prior.require(prior.driver.sha(root / path) == receipt["sha256"], "Reviewed packet changed")
    write_json(root / "validation_contract.json", contract)
    print("Staged18episodes/600s/USD10; isolated preflight and sealing required; zero API calls", flush=True)


def isolated_preflight(root, config, preparation):
    workspace = root / "preflight"
    prior.require(not workspace.exists(), "Preserve previous preflight; inspect before retry")
    shutil.copytree(root / "executive", workspace)
    library = Path(config["verus_bin"]).parent / "vstd"
    hidden = [REPO / "AGENTS.md", preparation / "sources/card-056/candidate.rs",
              preparation / "packets/temporal-transfer/p1.md", root / "config.json",
              root / "packets/semantic-equality/p2.md", Path(config["env_file"])]
    settings = {"hidden": [str(path) for path in hidden], "library": str(library),
                "verus": config["verus_bin"], "lynette": config["lynette_bin"]}
    write_json(workspace / "probe.json", settings)
    probe = '''import json,socket,subprocess
from pathlib import Path
settings=json.loads(Path('probe.json').read_text())
for path in settings['hidden']:
    try: Path(path).read_bytes()
    except OSError: pass
    else: raise AssertionError('Private source visible')
assert Path('SKILL.md').read_text()
assert not Path('cards.json').exists() and not Path('references').exists()
library=Path(settings['library'])/'set.rs'
assert library.read_bytes()
try: library.open('r+b')
except OSError: pass
else: raise AssertionError('Writable library')
try: socket.create_connection(('1.1.1.1',443),timeout=1)
except OSError: pass
else: raise AssertionError('External network reachable')
Path('input.rs').write_text('use vstd::prelude::*;\\nverus! { proof fn probe() {} }\\nfn main() {}\\n')
Path('candidate.rs').write_text(Path('input.rs').read_text().replace('probe() {}','probe() { assert(1int == 1int); }'))
for command in ([settings['verus'],'candidate.rs'],[settings['lynette'],'compare','-t','input.rs','candidate.rs']):
    result=subprocess.run(command,capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stdout+result.stderr
print('PASS: private sources/other packets hidden, no bank, library read-only, network blocked, dual checks')
'''
    isolation = prior.ActorIsolationConfig(Path(config["scratch_root"]), library.parent,
        Path(config["rust_root"]), 18136, (REPO, preparation, root / "config.json", Path(config["env_file"]), Path(config["data_root"])))
    command = prior.build_isolated_actor_command(["/usr/bin/python3", "-c", probe], workspace=workspace,
        codex_bin=Path("/usr/bin/python3"), lynette_bin=Path(config["lynette_bin"]), config=isolation)
    checked = subprocess.run(command, env=prior._codex_environment(None), capture_output=True, text=True, timeout=180)
    write_json(root / "preflight.json", {"paid_calls": 0, "returncode": checked.returncode,
        "stdout": checked.stdout, "stderr": checked.stderr})
    prior.require(checked.returncode == 0, "Isolated preflight failed; preserved output")


def seal(root):
    prior.require(not (root / "review_receipt.json").exists(), "Contract already sealed")
    contract = prior.read(root / "validation_contract.json")
    config = prior.read(root / "config.json")
    preparation = Path(contract["preparation_root"])
    isolated_preflight(root, config, preparation)
    paths = [path for path in root.rglob("*") if path.is_file() and path.name != "validation_contract.json"]
    for folder in ("scripts", "skill-evolution-pilot/src", "skillopt-verusage/src"):
        paths.extend((REPO / folder).rglob("*.py"))
    paths.extend(path for path in Path(config["verus_bin"]).parent.rglob("*") if path.is_file())
    paths.extend(path for path in preparation.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    contract["input_hashes"].update({str(path.resolve()): prior.driver.sha(path) for path in paths})
    write_json(root / "validation_contract.json", contract)
    write_json(root / "review_receipt.json", {"decision": "APPROVE_WITH_NONBLOCKING_NOTES",
        "contract_sha256": prior.driver.sha(root / "validation_contract.json"), "paid_calls": 0,
        "reviewer": "coding assistant source/material/runtime review, not independent review",
        "authorization": AUTHORIZATION, "blocking_issues": [],
        "nonblocking_notes": [contract["caveat"], "Deadline-dual parser is conservative; unsupported commands require trace review."]})
    check(root)
    print("Sealed18episodes/600s/USD10, zero API checks passed", flush=True)


def check(root):
    contract = prior.read(root / "validation_contract.json")
    expected = {"schema_version": "structural-skeleton-hard-v1", "expected_episodes": 18,
                "repeats": 2, "budget_usd": 10, "timeout_seconds": 600, "workers": 2,
                "model": "deepseek-v4-pro", "reasoning_effort": "max", "model_context_window": 1048576,
                "max_output_tokens_per_request": 131072, "provider_request_timeout_seconds": 1800,
                "transport_retry": False, "ordinary_retry": False, "sealed_test_access": False,
                "reference_proof_supplied": False, "installed_library_conditions": list(ARMS),
                "schedule": schedule(root), "cases": list(CASES), "authorization": AUTHORIZATION}
    for key, value in expected.items():
        prior.require(contract.get(key) == value, "Frozen setting changed: " + key)
    prior.require([item["id"] for item in contract["items"]] == [case["task"] for case in CASES], "Wrong cohort")
    prior.require(all(prior.driver.sha(path) == digest for path, digest in contract["input_hashes"].items()), "Frozen input changed")
    prior.require(prior.read(root / "preflight.json")["returncode"] == 0, "Preflight missing")
    for arm in ARMS:
        load_skill_artifact(Path(contract["bundle_paths"][arm]), contract["artifacts"][arm]["artifact_sha256"])
    prior.driver.check_review(root / "review_receipt.json", root / "validation_contract.json")
    return contract


def recognized_checks(command, output, exit_code):
    try:
        tokens = shlex.split(command)
        if "-lc" in tokens:
            command = tokens[tokens.index("-lc") + 1]
        elif tokens and tokens[0] in ("/bin/bash", "bash"):
            return set()
        segments = [shlex.split(segment.strip()) for segment in command.split("&&")]
    except (ValueError, IndexError):
        return set()
    if any(symbol in command for symbol in (";", "|", ">", "<", "`", "$", "\n")):
        return set()
    allowed = (["./tools/run_verus.sh", "candidate.rs"], ["./tools/run_lynette.sh"])
    if not segments or any(segment not in allowed for segment in segments) or exit_code != 0:
        return set()
    found = set()
    if allowed[0] in segments and re.search(r"verification results:: [1-9]\d* verified, 0 errors", output):
        found.add("verus")
    if allowed[1] in segments and "Files are different" not in output:
        found.add("lynette")
    return found


def deadline_audit(episode, timeout=600):
    result = prior.read(episode / "result.json")
    started_at = datetime.fromisoformat(result["started_at"])
    seen = set()
    starts = {}
    passed = {}
    observations = []
    unsupported = 0
    first = None
    for line_number, line in enumerate((episode / "agent_events.jsonl").read_text().splitlines(), 1):
        event = json.loads(line)
        elapsed = (datetime.fromisoformat(event["timestamp"]) - started_at).total_seconds()
        raw = event.get("data", {}).get("raw_codex_event", {})
        item = raw.get("item", {})
        candidate = event.get("candidate_sha256")
        if raw.get("type") == "item.started":
            starts[item.get("id")] = candidate
        checks = set()
        if raw.get("type") == "item.completed" and item.get("type") == "command_execution":
            if item.get("id") in seen:
                continue
            seen.add(item.get("id"))
            command = item.get("command", "")
            checks = recognized_checks(command, item.get("aggregated_output", ""), item.get("exit_code"))
            if any(name in command for name in ("run_verus.sh", "run_lynette.sh")) and not checks:
                unsupported += 1
            if not candidate or starts.get(item.get("id")) != candidate:
                checks = set()
        elif event.get("type") == "verifier" and event.get("actor") in ("verus", "lynette"):
            if event.get("data", {}).get("passed"):
                checks.add(event["actor"])
        if not candidate or not checks or elapsed < 0 or elapsed > timeout:
            continue
        passed.setdefault(candidate, set()).update(checks)
        observations.append({"line": line_number, "seconds": elapsed, "candidate_sha256": candidate,
                             "checks": sorted(checks)})
        if first is None and passed[candidate] == {"verus", "lynette"}:
            first = elapsed
    return {"observed_dual_within_deadline": first is not None,
            "first_confirmed_dual_seconds": first, "unconfirmed_or_failed_check_commands": unsupported,
            "evidence": observations,
            "limitation": "Conservative observation metric, not proof of absence. Piped/masked commands or changed-during-command hashes need manual review. Historical primary remains unchanged."}


def report(root):
    summary = prior.read(root / "summary.json")
    jobs = {prior.driver.episode_key(job): job for job in schedule(root)}
    rows = []
    for entry in summary["rows"]:
        row = result_dimensions(entry)
        key = entry["row"]["bridge_task_key"]
        episode = Path(entry["episode"])
        row["repeat"] = jobs[key]["repeat"]
        row["fixed_exposure_in_prompt"] = (episode / "prompt.txt").read_text() == expected_prompt(root, jobs[key])
        audit = deadline_audit(episode)
        write_json(episode / "deadline_dual_audit.json", audit)
        row["observed_dual_within_deadline"] = audit["observed_dual_within_deadline"]
        row["first_confirmed_dual_seconds"] = audit["first_confirmed_dual_seconds"]
        rows.append(row)
    with (root / "episodes.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["condition"])
        writer.writeheader()
        writer.writerows(rows)
    arms = {}
    for arm in ARMS:
        selected = [row for row in rows if row["condition"] == arm]
        arms[arm] = {"episodes": len(selected),
            "budgeted_dual_passes": sum(row["budgeted_dual_pass"] for row in selected),
            "strict_passes": sum(row["budgeted_dual_pass"] and row["fidelity"] == "V2_TRACE" for row in selected),
            "observed_deadline_dual_passes": sum(row["observed_dual_within_deadline"] for row in selected),
            "known_totals": {field: sum(row[field] for row in selected) for field in
                             ("actor_seconds", "prompt_tokens", "completion_tokens", "estimated_cost_usd", "uniform_off_peak_estimated_usd")}}
    write_json(root / "report.json", {"completed": len(rows), "expected": 18, "arms": arms, "rows": rows,
        "budget": prior.read(root / "budget.json"), "failures": summary["failures"],
        "inputs_unchanged": summary["reviewed_inputs_unchanged"], "bridge_drained": summary["bridge_drained"],
        "primary": AUTHORIZATION["primary"], "caveat": summary["caveat"]})


def run(root):
    contract = check(root)
    with (root / "execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior.require(not (root / "episodes").exists(), "No restart/replay of spent episodes")
        config = prior.read(root / "config.json")
        prior.credentials(config)
        guard = SharedBudgetGuard(root / "budget.json", approval_limit_usd=10, prior_spend_usd=0,
                                  optimizer_reserve_usd=0, request_reserve_usd=0)
        try:
            prior.driver.run(config, root, contract, expected_episodes=18, budget_guard=BudgetMux([guard]),
                             retrieval_auditor=lambda path: {"read_calls": 0, "mode": "fixed-prompt-exposure-no-bank"})
        finally:
            if (root / "summary.json").exists():
                report(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "seal", "check", "run", "report"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    root = prior.builder.output_root(args.output)
    if args.phase == "prepare":
        prior.require(args.preparation is not None and args.config is not None, "Missing inputs")
        prepare(root, args.preparation.resolve(), args.config.resolve())
    elif args.phase == "seal":
        seal(root)
    elif args.phase == "check":
        check(root)
        print("Frozen18episodes/600s/USD10 verified")
    elif args.phase == "report":
        report(root)
    else:
        run(root)


if __name__ == "__main__":
    main()

"""Replace two authorized infrastructure aborts and finish the hard pilot."""
from __future__ import annotations

import argparse
import copy
import fcntl
import math
from pathlib import Path
import shutil

import evaluate_structural_skeleton_hard as pilot
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import BudgetMux, write_json


evaluation = pilot.prior
RETRY_KEYS = {f"dev_{arm}--a23a4969155913255f76--repeat-0" for arm in ("p0", "p1")}
AUTHORIZATION = {**pilot.AUTHORIZATION, "budget_usd": 15,
    "basis": "User authorized replacing both technical interruptions and completing the other16 cells, raising the total campaign cap to USD15 including prior known/unknown charges."}


def prior_charge(state):
    evaluation.require(not state["reservations"], "Prior live reservations remain")
    amounts = [state[key] for key in ("prior_spend_usd", "target_spend_usd", "uncertain_spend_usd")]
    evaluation.require(all(math.isfinite(value) and value >= 0 for value in amounts), "Invalid prior charges")
    charge = sum(amounts)
    evaluation.require(charge < 15, "No remaining authorized budget")
    return charge


def validate_attempts(contract, summary):
    evaluation.require(summary["bridge_drained"] and summary["reviewed_inputs_unchanged"], "Prior run not safely stopped")
    rows = {entry["row"]["bridge_task_key"]: entry["row"] for entry in summary["rows"]}
    evaluation.require(len(summary["rows"]) == len(rows) == 2 and set(rows) == RETRY_KEYS, "Unexpected prior attempts")
    keys = [evaluation.driver.episode_key(job) for job in contract["schedule"]]
    evaluation.require(len(keys) == len(set(keys)) == 18 and RETRY_KEYS <= set(keys), "Unexpected matrix")
    for row in rows.values():
        evaluation.require(not row["timed_out"] and not row["proof_solved"]
            and row["codex_returncode"] == 1 and row["fidelity"] == "V0_INVALID",
            "Only the two audited infrastructure aborts may be replaced")


def prepare(parent_root, root):
    parent = pilot.check(parent_root)
    validate_attempts(parent, evaluation.read(parent_root / "summary.json"))
    state = evaluation.read(parent_root / "budget.json")
    charge = prior_charge(state)
    evaluation.require({path.name for path in (parent_root / "episodes").iterdir()} == RETRY_KEYS, "Unexpected episode directories")
    for key in RETRY_KEYS:
        events = (parent_root / "episodes" / key / "codex_events.raw.jsonl").read_text()
        evaluation.require("Provider bridge halted pending review" in events, "Missing technical abort evidence")
    evaluation.require(not root.exists(), "Fresh continuation output required")
    root.mkdir(parents=True)
    for folder in ("executive", "packets", "runtime"):
        shutil.copytree(parent_root / folder, root / folder)
    shutil.copyfile(parent_root / "TASK.md", root / "TASK.md")
    config = evaluation.read(parent_root / "config.json")
    config["source_root"] = str(root / "runtime")
    write_json(root / "config.json", config)
    write_json(root / "authorization.json", AUTHORIZATION)
    pilot.isolated_preflight(root, config, Path(parent["preparation_root"]))
    contract = copy.deepcopy(parent)
    contract.update(schema_version="structural-skeleton-hard-continuation-v1", budget_usd=15,
        authorization=AUTHORIZATION, schedule=pilot.schedule(root),
        bundle_paths={arm: str(root / "executive") for arm in pilot.ARMS},
        expense_policy="USD15 campaign cap including all prior known charges and unknown-charge reserves; no automatic retries.",
        continuation={"prior_root": str(parent_root), "authorized_retry_keys": sorted(RETRY_KEYS),
            "unstarted_count": 16, "prior_conservative_charge_usd": charge,
            "prior_known_charge_usd": state["prior_spend_usd"] + state["target_spend_usd"],
            "prior_uncertain_reserve_usd": state["uncertain_spend_usd"],
            "reporting": "Exclude only the two pre-authorized infrastructure attempts from scored cells; preserve their records and charges. No best-of selection."})
    paths = [path for path in root.rglob("*") if path.is_file()]
    paths.extend(parent_root / name for name in ("validation_contract.json", "review_receipt.json", "summary.json", "budget.json", "provider_calls.jsonl"))
    paths.extend(path for path in (parent_root / "episodes").rglob("*") if path.is_file())
    paths.append(Path(__file__))
    contract["input_hashes"].update({str(path.resolve()): evaluation.driver.sha(path) for path in paths})
    write_json(root / "validation_contract.json", contract)
    write_json(root / "review_receipt.json", {"decision": "APPROVE_WITH_NONBLOCKING_NOTES",
        "contract_sha256": evaluation.driver.sha(root / "validation_contract.json"), "paid_calls": 0,
        "reviewer": "coding assistant continuation review, not independent review", "blocking_issues": [],
        "authorization": AUTHORIZATION, "nonblocking_notes": ["Provider availability is not guaranteed; future provider errors still stop scheduling."]})
    check(root)
    print(f"Prepared18episodes/600s/USD15 total, prior conservative chargeUSD{charge:.9f}; zero paid calls", flush=True)


def check(root):
    contract = evaluation.read(root / "validation_contract.json")
    parent_root = Path(contract["continuation"]["prior_root"])
    parent = pilot.check(parent_root)
    validate_attempts(parent, evaluation.read(parent_root / "summary.json"))
    mutable = {"schema_version", "budget_usd", "authorization", "schedule", "bundle_paths", "expense_policy", "input_hashes"}
    for key, value in parent.items():
        if key not in mutable:
            evaluation.require(contract[key] == value, "Method changed: " + key)
    evaluation.require(contract["schema_version"] == "structural-skeleton-hard-continuation-v1"
        and contract["budget_usd"] == 15 and contract["authorization"] == AUTHORIZATION, "Unauthorized continuation")
    evaluation.require(contract["schedule"] == pilot.schedule(root), "Schedule changed")
    evaluation.require(contract["bundle_paths"] == {arm: str(root / "executive") for arm in pilot.ARMS}, "Bundle paths changed")
    evaluation.require(contract["continuation"]["prior_conservative_charge_usd"] == prior_charge(evaluation.read(parent_root / "budget.json")), "Budget carry changed")
    evaluation.require(contract["continuation"]["authorized_retry_keys"] == sorted(RETRY_KEYS)
        and contract["continuation"]["unstarted_count"] == 16, "Retry scope changed")
    evaluation.require(all(evaluation.driver.sha(path) == digest for path, digest in contract["input_hashes"].items()), "Frozen input changed")
    evaluation.require(evaluation.read(root / "preflight.json")["returncode"] == 0, "Preflight failed")
    for path in (parent_root / "packets").rglob("*.md"):
        evaluation.require(path.read_bytes() == (root / path.relative_to(parent_root)).read_bytes(), "Packet changed")
    for relative in ("TASK.md", "executive/SKILL.md"):
        evaluation.require((parent_root / relative).read_bytes() == (root / relative).read_bytes(), "Common prompt changed")
    evaluation.driver.check_review(root / "review_receipt.json", root / "validation_contract.json")
    return contract


def report(root):
    pilot.report(root)
    result = evaluation.read(root / "report.json")
    result["continuation"] = evaluation.read(root / "validation_contract.json")["continuation"]
    result["excluded_prior_attempts"] = sorted(RETRY_KEYS)
    result["campaign_known_charge_usd"] = result["continuation"]["prior_known_charge_usd"] + result["budget"]["target_spend_usd"]
    result["campaign_uncertain_reserve_usd"] = result["continuation"]["prior_uncertain_reserve_usd"] + result["budget"]["uncertain_spend_usd"]
    write_json(root / "report.json", result)


def run(root):
    contract = check(root)
    with (root / "execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        evaluation.require(not (root / "episodes").exists(), "Already started; no automatic replay")
        config = evaluation.read(root / "config.json")
        evaluation.credentials(config)
        guard = SharedBudgetGuard(root / "budget.json", approval_limit_usd=15,
            prior_spend_usd=contract["continuation"]["prior_conservative_charge_usd"],
            optimizer_reserve_usd=0, request_reserve_usd=0)
        try:
            evaluation.driver.run(config, root, contract, expected_episodes=18, budget_guard=BudgetMux([guard]),
                retrieval_auditor=lambda path: {"read_calls": 0, "mode": "fixed-prompt-exposure-no-bank"})
        finally:
            if (root / "summary.json").exists():
                report(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "check", "run", "report"))
    parser.add_argument("--prior", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = evaluation.builder.output_root(args.output)
    if args.phase == "prepare":
        evaluation.require(args.prior is not None, "Missing prior output")
        prepare(args.prior.resolve(), root)
    elif args.phase == "check":
        check(root)
        print("Frozen continuation verified")
    elif args.phase == "run":
        run(root)
    else:
        report(root)

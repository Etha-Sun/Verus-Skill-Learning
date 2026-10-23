"""Fixed v2 proof organization, two reviewed train-derived guidance conditions."""
from __future__ import annotations

import argparse
import csv
import fcntl
from pathlib import Path
import shutil
import subprocess

import evaluate_structural_skeleton_hard as hard
from continue_card_organization_evaluation import result_dimensions
from local_instantiation_extraction import ARMS, AUTHORIZATION, TRAIN, check as check_extraction, guards, read, sha
from skill_evolution_pilot.codex_runner import build_prompt
from skillopt_verusage.guarded_deepseek import BudgetMux, write_json

REPO = Path(__file__).resolve().parents[1]
prior = hard.prior
CASES = hard.CASES


def protocol(parent):
    if (parent / "recovery.json").exists():
        import recover_local_instantiation as recovery
        recovery.check(parent)
        return recovery.AUTHORIZATION, recovery.guards
    check_extraction(parent)
    return AUTHORIZATION, guards


def schedule(root):
    return [{"id": case["task"], "condition": arm, "repeat": repeat,
             "knowledge_path": str(root / "packets" / case["packet"] / (arm + ".md"))}
            for repeat in range(2) for i, case in enumerate(CASES)
            for arm in (ARMS if (i + repeat) % 2 == 0 else ARMS[::-1])]


def selected_cards(parent, selection, arm, family):
    bank = read(parent / "learning/banks" / arm / "cards.json")["cards"]
    cards = {card["id"]: card for card in bank}
    decisions = selection["arms"][arm]
    if len(decisions) != len(cards) or {d["id"] for d in decisions} != set(cards):
        raise ValueError("Every candidate needs a recorded decision")
    selected = []
    for decision in decisions:
        card = cards[decision["id"]]
        import hashlib
        if hashlib.sha256(card["content"].encode()).hexdigest() != decision["content_sha256"]:
            raise ValueError("Reviewed candidate changed")
        if not decision["reason"] or decision["decision"] not in ("accept", "reject"):
            raise ValueError("Missing candidate review")
        if not set(decision["families"]) <= {case["packet"] for case in CASES}:
            raise ValueError("Unknown exposure family")
        if decision["decision"] == "reject" and decision["families"]:
            raise ValueError("Rejected card cannot be exposed")
        if family in decision["families"]:
            selected.append(card)
    if not selected:
        raise ValueError("No reviewed guidance for a planned cell; report coverage gap before evaluation")
    return selected


def preflight(root, config, parent):
    workspace = root / "preflight"
    shutil.copytree(root / "executive", workspace)
    library = Path(config["verus_bin"]).parent / "vstd"
    hidden = [REPO / "AGENTS.md", parent / "learning/sources" / (TRAIN[0] + ".json"),
              parent / "learning/banks/old/cards.json", root / "config.json",
              root / "packets/semantic-equality/revised.md", Path(config["env_file"])]
    write_json(workspace / "probe.json", {"hidden": list(map(str, hidden)), "library": str(library),
        "verus": config["verus_bin"], "lynette": config["lynette_bin"]})
    probe = '''import json,socket,subprocess
from pathlib import Path
s=json.loads(Path('probe.json').read_text())
for p in s['hidden']:
    try: Path(p).read_bytes()
    except OSError: pass
    else: raise AssertionError('Private input visible: '+p)
assert Path('SKILL.md').read_text()
assert not Path('cards.json').exists() and not Path('references').exists()
p=Path(s['library'])/'set.rs'
assert p.read_bytes()
try: p.open('r+b')
except OSError: pass
else: raise AssertionError('Writable library')
try: socket.create_connection(('1.1.1.1',443),timeout=1)
except OSError: pass
else: raise AssertionError('External network reachable')
Path('input.rs').write_text('use vstd::prelude::*;\\nverus! { proof fn probe() {} }\\nfn main() {}\\n')
Path('candidate.rs').write_text(Path('input.rs').read_text().replace('probe() {}','probe() { assert(1int == 1int); }'))
for cmd in ([s['verus'],'candidate.rs'],[s['lynette'],'compare','-t','input.rs','candidate.rs']):
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
    assert r.returncode==0,r.stdout+r.stderr
print('PASS: private learning evidence and other packets hidden; read-only library; blocked network; dual checks')
'''
    isolation = prior.ActorIsolationConfig(Path(config["scratch_root"]), library.parent,
        Path(config["rust_root"]), 18136, (REPO, parent / "learning", root / "config.json",
        Path(config["env_file"]), Path(config["data_root"])))
    command = prior.build_isolated_actor_command(["/usr/bin/python3", "-c", probe], workspace=workspace,
        codex_bin=Path("/usr/bin/python3"), lynette_bin=Path(config["lynette_bin"]), config=isolation)
    result = subprocess.run(command, env=prior._codex_environment(None), capture_output=True, text=True, timeout=180)
    write_json(root / "preflight.json", {"paid_calls": 0, "returncode": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr})
    prior.require(result.returncode == 0, "Isolated zero-API preflight failed")


def prepare(root, preparation):
    parent = root.parent
    authorization, _ = protocol(parent)
    prior.require(read(parent / "learning/completed.json")["requests"] == 4, "Extraction incomplete")
    selection_path = parent / "learning/selection.json"
    selection = read(selection_path)
    prior.require(selection["review_completed"] is True and not root.exists(), "Need reviewed candidates and fresh evaluation root")
    for name in ("budget-total.json", "budget-extraction.json"):
        state = read(parent / name)
        prior.require(not state["reservations"] and state["uncertain_requests"] == 0, "Unresolved extraction charges")
    config = read(parent / "config.json")
    for key in ("codex_bin", "lynette_bin"):
        prior.require(sha(config[key]) == prior.HISTORICAL[key], "Historical tool changed")
    prior.require(sha(config["catalog"]) == prior.HISTORICAL["models.json"], "Catalog changed")
    prior.require(sha(Path(config["verus_bin"]).parent / "rust_verify") == prior.LOCAL_RUST_VERIFY, "Verifier changed")
    (root / "executive").mkdir(parents=True)
    shutil.copyfile(preparation / "common/SKILL.md", root / "executive/SKILL.md")
    shutil.copyfile(preparation / "common/TASK.md", root / "TASK.md")
    prior.require((root / "TASK.md").read_text() == build_prompt(installed_library_root=Path(config["verus_bin"]).parent / "vstd"), "TASK changed")
    exposure = {}
    for family in sorted({case["packet"] for case in CASES}):
        base_path = preparation / "packets" / family / "p2.md"
        material = read(preparation / "material_manifest.json")[str(base_path.relative_to(preparation))]
        prior.require(sha(base_path) == material["sha256"], "Reviewed v2 material changed")
        base = base_path.read_text()
        for arm in ARMS:
            selected = selected_cards(parent, selection, arm, family)
            packet = root / "packets" / family / (arm + ".md")
            packet.parent.mkdir(parents=True, exist_ok=True)
            packet.write_text(base.rstrip() + "\n\n## Additional proof guidance\n\n" +
                "\n\n".join(card["content"] for card in selected) + "\n")
            exposure[family + "/" + arm] = {"card_ids": [card["id"] for card in selected],
                "v2_sha256": sha(base_path), "packet_sha256": sha(packet), "characters": len(packet.read_text())}
    write_json(root / "exposure.json", exposure)
    (root / "runtime").mkdir()
    shutil.copyfile(config["catalog"], root / "runtime/models.json")
    config["source_root"] = str(root / "runtime")
    write_json(root / "config.json", config)
    contract = prior.driver.prepare(root / "config.json", root / "executive", root / "executive", root,
        task_ids=tuple(case["task"] for case in CASES), installed_library_conditions=ARMS)
    contract.update(schema_version="local-instantiation-evaluation-v1", expected_episodes=12, repeats=2,
        budget_usd=authorization["evaluation_usd"], authorization=authorization, schedule=schedule(root), cases=list(CASES),
        model_context_window=1048576, max_output_tokens_per_request=131072,
        provider_request_timeout_seconds=1800, transport_retry=False,
        expense_policy="Approved phase caps from authorization, total USD15 including all inherited failed/unknown costs; no automatic paid retries.",
        caveat="Known three-task development diagnostic, two repeats. Fixed v2 plus train-derived old/new guidance; content and representation intervention, not pure formatting. De Morgan transfer coverage is uncertain. No unseen generalization claim.")
    preflight(root, config, parent)
    paths = [p for p in root.rglob("*") if p.is_file() and p.name != "validation_contract.json"]
    paths += [selection_path, parent / "learning/selection_policy.json", parent / "learning/source_recheck.json",
              parent / "learning/contract.json", parent / "authorization.json"]
    paths += [p for p in (parent / "learning/banks").rglob("*") if p.is_file()]
    for folder in ("scripts", "skill-evolution-pilot/src", "skillopt-verusage/src"):
        paths += list((REPO / folder).rglob("*.py"))
    paths += [p for p in Path(config["verus_bin"]).parent.rglob("*") if p.is_file()]
    contract["input_hashes"].update({str(p.resolve()): sha(p) for p in paths})
    write_json(root / "validation_contract.json", contract)
    write_json(root / "review_receipt.json", {"decision": "APPROVE_WITH_NONBLOCKING_NOTES",
        "contract_sha256": sha(root / "validation_contract.json"),
        "reviewer": "coding assistant candidate/provenance/runtime review; not independent review",
        "authorization": authorization, "blocking_issues": [], "nonblocking_notes": [contract["caveat"]]})
    check(root)
    print(f"Frozen 12 episodes, 600 seconds, USD{authorization['evaluation_usd']} evaluation/USD15 total; zero API preflight passed", flush=True)


def check(root):
    contract = read(root / "validation_contract.json")
    authorization, _ = protocol(root.parent)
    expected = {"authorization": authorization, "schedule": schedule(root), "expected_episodes": 12,
        "repeats": 2, "budget_usd": authorization["evaluation_usd"], "timeout_seconds": 600, "workers": 2,
        "model": "deepseek-v4-pro", "reasoning_effort": "max", "ordinary_retry": False,
        "transport_retry": False, "sealed_test_access": False, "reference_proof_supplied": False}
    prior.require(all(contract.get(k) == v for k, v in expected.items()), "Frozen evaluation contract changed")
    prior.require(all(sha(p) == digest for p, digest in contract["input_hashes"].items()), "Reviewed input changed")
    prior.require(read(root / "preflight.json")["returncode"] == 0, "Preflight missing")
    prior.driver.check_review(root / "review_receipt.json", root / "validation_contract.json")
    return contract


def report(root):
    summary = read(root / "summary.json")
    jobs = {prior.driver.episode_key(job): job for job in schedule(root)}
    rows = []
    for entry in summary["rows"]:
        row = result_dimensions(entry)
        job = jobs[entry["row"]["bridge_task_key"]]
        episode = Path(entry["episode"])
        audit = hard.deadline_audit(episode)
        write_json(episode / "deadline_dual_audit.json", audit)
        row.update(repeat=job["repeat"], fixed_exposure_in_prompt=(episode / "prompt.txt").read_text() == hard.expected_prompt(root, job),
            observed_dual_within_deadline=audit["observed_dual_within_deadline"],
            first_confirmed_dual_seconds=audit["first_confirmed_dual_seconds"],
            capped_first_dual_seconds=audit["first_confirmed_dual_seconds"] if audit["first_confirmed_dual_seconds"] is not None else 600,
            first_confirmed_verus_seconds=min((e["seconds"] for e in audit["evidence"] if "verus" in e["checks"]), default=None))
        rows.append(row)
    with (root / "episodes.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["condition"])
        writer.writeheader(); writer.writerows(rows)
    write_json(root / "report.json", {"rows": rows, "expected": 12, "completed": len(rows),
        "failures": summary["failures"], "inputs_unchanged": summary["reviewed_inputs_unchanged"],
        "budget_total": read(root.parent / "budget-total.json"), "budget_evaluation": read(root.parent / "budget-evaluation.json"),
        "mechanism_audit": "Pending manual observable-action review; do not infer a procedure from final-code similarity.",
        "caveat": summary["caveat"]})


def run(root):
    contract = check(root)
    _, phase_guards = protocol(root.parent)
    with (root / "execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior.require(not (root / "episodes").exists(), "No paid restart/replay")
        config = read(root / "config.json")
        prior.credentials(config)
        try:
            prior.driver.run(config, root, contract, expected_episodes=12,
                budget_guard=BudgetMux(phase_guards(root.parent, "evaluation")),
                retrieval_auditor=lambda path: {"read_calls": 0, "mode": "fixed-prompt-exposure-no-bank"})
        finally:
            if (root / "summary.json").exists():
                report(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "check", "run", "report"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preparation", type=Path)
    args = parser.parse_args()
    root = prior.builder.output_root(args.output)
    if args.phase == "prepare":
        prepare(root, args.preparation)
    else:
        {"check": check, "run": run, "report": report}[args.phase](root)


if __name__ == "__main__":
    main()

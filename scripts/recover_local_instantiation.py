"""One explicitly authorized extraction recovery; inherit all prior charges and evidence."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil

import local_instantiation_extraction as initial
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
from skillopt_verusage.budget_guard import SharedBudgetGuard

AUTHORIZATION = {**initial.AUTHORIZATION, "extraction_usd": 7, "evaluation_usd": 8,
    "optimizer_requests": 5, "recovery_requests": 2, "explicit_retry_requests": 1,
    "basis": "User explicitly approved one recovery: USD7 extraction/USD8 evaluation, USD15 total unchanged, with all prior costs retained."}


def guards(root, phase):
    inherited = initial.read(root / "recovery.json")["inherited_cost_usd"]
    return [SharedBudgetGuard(root / name, approval_limit_usd=cap, prior_spend_usd=prior,
                              optimizer_reserve_usd=0, request_reserve_usd=0)
            for name, cap, prior in (("budget-total.json", 15, inherited),
                (f"budget-{phase}.json", 7 if phase == "extraction" else 8, inherited if phase == "extraction" else 0))]


class ReminderClient:
    """Only change the output contract; never alter source evidence or the seed."""
    def __init__(self, real, reminder):
        self.real, self.reminder = real, reminder

    def request(self, kwargs):
        from skillopt_verusage.campaign_evidence import expand_strings
        # Validate the transformation on every admission and actual request.
        kwargs = dict(kwargs)
        packet = json.loads(kwargs["user"])
        before = expand_strings(packet)
        packet["output_contract_reminder"].update(self.reminder)
        after = expand_strings(packet)
        if ({k: v for k, v in before.items() if k != "output_contract_reminder"}
                != {k: v for k, v in after.items() if k != "output_contract_reminder"}):
            raise ValueError("Reminder transformation changed evidence")
        kwargs["user"] = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
        return kwargs

    def payload(self, **kwargs):
        return self.real.payload(**self.request(kwargs))

    def admit(self, **kwargs):
        return self.real.admit(**self.request(kwargs))

    def call(self, **kwargs):
        return self.real.call(**self.request(kwargs))


def client(root, *, paid=False):
    return ReminderClient(GuardedDeepSeek(root=root / "learning/calls/revised",
        api_key=os.environ["DEEPSEEK_API_KEY"] if paid else "offline-no-provider-call",
        guards=guards(root, "extraction") if paid else [], ledger=root / "learning/provider_calls.jsonl",
        output_cap=16384, tokenizer_path=root / "learning/tokenizer/tokenizer.json",
        tokenizer_sha256=initial.TOKENIZER_SHA, capture_public_payloads=True),
        initial.read(root / "learning/output-reminder.json"))


def prepare(parent, root):
    initial.check(parent)
    audit = initial.read(parent / "learning/failure_audit.json")
    state = initial.read(parent / "budget-total.json")
    if (root.exists() or audit["paid_requests"] != 3 or audit["actor_episodes"] != 0
            or state["reservations"] or state["uncertain_requests"] or state["settled_requests"] != 3):
        raise ValueError("Recovery requires the reviewed stopped three-request attempt")
    root.mkdir(parents=True)
    shutil.copyfile(parent / "config.json", root / "config.json")
    shutil.copyfile(parent / "source_receipt.json", root / "source_receipt.json")
    for folder in ("sources", "tokenizer", "banks/old"):
        shutil.copytree(parent / "learning" / folder, root / "learning" / folder)
    for name in ("seed.md", "review-old.json", "selection_policy.json", "source_recheck.json"):
        shutil.copyfile(parent / "learning" / name, root / "learning" / name)
    (root / "learning/systems").mkdir()
    shutil.copyfile(initial.DOC / "SYSTEM.local-instantiation-v3.draft.txt", root / "learning/systems/revised.txt")
    shutil.copyfile(initial.DOC / "OUTPUT_CONTRACT.local-instantiation-v3.draft.json", root / "learning/output-reminder.json")
    write_json(root / "recovery.json", {"prior_root": str(parent), "prior_contract_sha256": initial.sha(parent / "learning/contract.json"),
        "inherited_cost_usd": state["target_spend_usd"], "retained_old_bank_sha256": initial.sha(parent / "learning/banks/old/cards.json"),
        "failed_revision2_response_retained": True, "new_requests": 2, "authorization": AUTHORIZATION})
    write_json(root / "authorization.json", AUTHORIZATION)
    transport = client(root)
    recorder = initial.OfflineRecorder(root / "learning/offline-requests/revised", transport)
    initial.module_for("revised", (root / "learning/systems/revised.txt").read_text()).update_cards(
        initial.load_groups(root), root / "learning/seed.md", root / "learning/offline-native/revised", recorder,
        workers=1, admit=transport.admit)
    for path in (root / "learning/offline-requests/revised").glob("*.json"):
        if initial.read(path) != initial.read(parent / "learning/retry-v3-offline" / path.name):
            raise ValueError("Actual adapter differs from approved offline revision3 request")
    prior_files = [parent / "learning/contract.json", parent / "learning/failure_audit.json", parent / "learning/stopped.json",
                   parent / "budget-total.json", parent / "budget-extraction.json"]
    paths = [p for p in root.rglob("*") if p.is_file()] + prior_files
    paths += [Path(__file__), Path(initial.__file__)]
    paths += [Path(p) for p in initial.read(parent / "learning/contract.json")["input_hashes"]]
    write_json(root / "learning/contract.json", {"schema_version": "local-instantiation-recovery-v1",
        "authorization": AUTHORIZATION, "source_evidence_unchanged": True, "new_requests": 2,
        "retained_old_requests": 2, "failed_prior_requests": 1, "optimizer": "deepseek-v4-pro", "effort": "high",
        "output_cap": 16384, "workers": 1, "input_hashes": {str(p.resolve()): initial.sha(p) for p in paths}})
    check(root)
    print("Frozen authorized recovery, two complete requests, inherited costs retained; zero API calls", flush=True)


def check(root):
    contract = initial.read(root / "learning/contract.json")
    if contract["authorization"] != AUTHORIZATION or any(initial.sha(p) != h for p, h in contract["input_hashes"].items()):
        raise ValueError("Frozen recovery input changed")
    return contract


def extract(root):
    check(root)
    with (root / "learning/execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / "learning/started.json").exists():
            raise ValueError("Authorized recovery is one attempt only; no automatic restart")
        write_json(root / "learning/started.json", {"authorization": AUTHORIZATION})
        initial.prior.credentials(initial.read(root / "config.json"))
        try:
            transport = client(root, paid=True)
            initial.module_for("revised", (root / "learning/systems/revised.txt").read_text()).update_cards(
                initial.load_groups(root), root / "learning/seed.md", root / "learning/banks/revised", transport,
                workers=1, admit=transport.admit)
            write_json(root / "learning/completed.json", {"status": "awaiting_manual_candidate_review", "requests": 4,
                "new_requests": 2, "retained_old_requests": 2, "aggregate_paid_requests_including_failure": 5})
            print("Recovery extraction complete; manual candidate review still required", flush=True)
        except Exception as error:
            write_json(root / "learning/stopped.json", {"type": type(error).__name__, "reason": str(error), "automatic_retry": False})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "check", "extract"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prior", type=Path)
    args = parser.parse_args()
    root = initial.prior.builder.output_root(args.output)
    if args.phase == "prepare":
        prepare(args.prior, root)
    else:
        {"check": check, "extract": extract}[args.phase](root)


if __name__ == "__main__":
    main()

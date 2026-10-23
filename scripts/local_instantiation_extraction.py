"""Train-only, paired native Reflect extraction with frozen inputs and no paid retries."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

import evaluate_card_organization as prior
from skillopt_verusage import native_card_update as native
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "research_memory/projects/verus_self_evolving/experiments/20261019-local-instantiation-skill-plan"
TRAIN = ("dfdac48fe9eb152881db", "46f4d879d37da0eb8835", "198a95322505bae4f6f4", "a3c9af1afebbd8d5fe93")
DEV = ("a23a4969155913255f76", "9b9f6ccef89db4103c7f", "aded79905be896942897")
ARMS = ("old", "revised")
TOKENIZER_SHA = "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf"
AUTHORIZATION = {"total_usd": 15, "extraction_usd": 5, "evaluation_usd": 10,
    "optimizer_requests": 4, "episodes": 12, "repeats": 2, "timeout_seconds": 600,
    "basis": "User authorized server background experiment, then explicitly adjusted caps to USD5/USD10.",
    "automatic_paid_retry": False, "sealed_test_access": False}


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guards(root, phase):
    return [SharedBudgetGuard(root / name, approval_limit_usd=cap, prior_spend_usd=0,
                              optimizer_reserve_usd=0, request_reserve_usd=0)
            for name, cap in (("budget-total.json", 15), (f"budget-{phase}.json", 5 if phase == "extraction" else 10))]


def representation_audit(response, groups, arm):
    native.audit_response(response, groups)
    for card in response["cards"]:
        content = card["content"]
        if any(ident in json.dumps(card) for ident in DEV):
            raise ValueError("Development provenance in train-only card")
        labels = re.findall(r"\*\*(Trigger|Action|Why|Validate|Avoid when):\*\*", content)
        if labels != ["Trigger", "Action", "Why", "Validate", "Avoid when"]:
            raise ValueError("Exactly five ordered fields required")
        spans = list(re.finditer(r"`([^`\n]+)`", content))
        if content.count("`") != 2 * len(spans):
            raise ValueError("Malformed inline fragment")
        if arm == "old" and spans:
            raise ValueError("Old prose-only condition contains inline code")
        if len(spans) > 2:
            raise ValueError("More than two optional fragments")
        start = content.index("**Action:**")
        end = content.index("**Why:**")
        for match in spans:
            fragment = match.group(1)
            if not start < match.start() < match.end() <= end or len(fragment) > 160:
                raise ValueError("Fragment must be short and confined to Action")
            if re.search(r"[;{}\n]|\b(?:assert|assume|admit|proof|fn|forall|exists|choose)\b", fragment):
                raise ValueError("Statement or complete proof fragment")
    # These are syntax/provenance gates, not a semantic leakage or efficacy certificate.
    # Deployment still requires manual review of each claim and training segment.


def module_for(arm, system):
    spec = importlib.util.spec_from_file_location("local_card_update_" + arm, native.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SYSTEM = system
    module.audit_response = lambda response, groups: representation_audit(response, groups, arm)
    return module


def load_groups(root):
    items = read(REPO / "fixed-claude-stratified-80-seed20260814/train/items.json")
    if not set(TRAIN) <= {item["id"] for item in items}:
        raise ValueError("Source not allowlisted training data")
    groups = [read(root / "learning/sources" / (ident + ".json")) for ident in TRAIN]
    for ident, group in zip(TRAIN, groups):
        if group["source_task"] != ident or len(group["trace_ids"]) != 4 or len(group["forks"]) != 3:
            raise ValueError("Incomplete original-plus-three-forks group")
        if any(dev in json.dumps(group) for dev in DEV):
            raise ValueError("Development task in extraction input")
        for trace in [group["original"]["complete_trace"]] + [fork["complete_suffix"] for fork in group["forks"]]:
            if not trace["events"] or not trace["snapshots"]["chain"] or not trace["final_source"]:
                raise ValueError("Missing complete historical evidence")
    return groups


def client(root, arm, *, paid=False):
    return GuardedDeepSeek(root=root / "learning/calls" / arm,
        api_key=os.environ["DEEPSEEK_API_KEY"] if paid else "offline-no-provider-call",
        guards=guards(root, "extraction") if paid else [],
        ledger=root / "learning/provider_calls.jsonl", output_cap=16384,
        tokenizer_path=root / "learning/tokenizer/tokenizer.json", tokenizer_sha256=TOKENIZER_SHA,
        capture_public_payloads=True)


class OfflineRecorder:
    def __init__(self, root, real):
        self.root, self.real, self.users = root, real, []

    def call(self, *, system, user, name, cap):
        from skillopt_verusage.campaign_evidence import expand_strings
        packet = expand_strings(json.loads(user))
        self.users.append(user)
        write_json(self.root / (name + ".json"), self.real.payload(system=system, user=user, cap=cap))
        return json.dumps({"trace_analyses": [{"trace_id": tid, "observation": "Offline plumbing check only."}
            for group in packet["task_groups"] for tid in group["trace_ids"]], "cards": []}), {}


def prepare(root):
    if (root / "learning/contract.json").exists():
        raise ValueError("Extraction already frozen")
    groups = load_groups(root)
    systems = {"old": native.SYSTEM, "revised": (DOC / "SYSTEM.local-instantiation-v2.draft.txt").read_text()}
    systems_dir = root / "learning/systems"
    systems_dir.mkdir()
    seed = root / "learning/seed.md"
    seed.write_bytes((REPO / "skillopt-verusage/skills/initial.md").read_bytes())
    all_users = []
    for arm in ARMS:
        (systems_dir / (arm + ".txt")).write_text(systems[arm])
        transport = client(root, arm)
        recorder = OfflineRecorder(root / "learning/offline-requests" / arm, transport)
        module_for(arm, systems[arm]).update_cards(groups, seed, root / "learning/offline-native" / arm,
            recorder, workers=1, admit=transport.admit)
        all_users.append(recorder.users)
    if all_users[0] != all_users[1] or len(all_users[0]) != 2:
        raise ValueError("Arms must use identical complete user evidence and two batches")
    paths = [Path(__file__), Path(native.__file__), REPO / "fixed-claude-stratified-80-seed20260814/train/items.json",
             root / "config.json", root / "source_receipt.json"]
    paths += [path for path in (root / "learning").rglob("*") if path.is_file()]
    for module in ("guarded_deepseek", "campaign_evidence", "budget_guard", "text_context", "codex_deepseek_bridge"):
        paths.append(REPO / "skillopt-verusage/src/skillopt_verusage" / (module + ".py"))
    import skillopt.gradient.reflect as reflect
    paths.append(Path(reflect.__file__))
    contract = {"schema_version": "local-instantiation-extraction-v1", "authorization": AUTHORIZATION,
        "train_ids": list(TRAIN), "pairs": [[g["source_task"] for g in pair] for pair in native.paired_groups(groups)],
        "optimizer": "deepseek-v4-pro", "effort": "high", "output_cap": 16384, "workers": 1,
        "same_user_payload_both_arms": True, "full_evidence": True, "manual_review_before_actor": True,
        "fragment_gate": "At most two inline Action fragments, each <=160 characters; semantic manual review required.",
        "input_hashes": {str(path.resolve()): sha(path) for path in paths}}
    write_json(root / "authorization.json", AUTHORIZATION)
    write_json(root / "learning/contract.json", contract)
    print("Frozen complete train-only extraction; four requests admitted offline; zero paid calls", flush=True)


def check(root):
    contract = read(root / "learning/contract.json")
    if contract["authorization"] != AUTHORIZATION or any(sha(p) != digest for p, digest in contract["input_hashes"].items()):
        raise ValueError("Frozen extraction input changed")
    return contract


def extract(root):
    check(root)
    with (root / "learning/execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = root / "learning/started.json"
        if marker.exists():
            raise ValueError("No automatic paid restart; inspect preserved attempt")
        write_json(marker, {"authorization": AUTHORIZATION})
        prior.credentials(read(root / "config.json"))
        groups = load_groups(root)
        try:
            for arm in ARMS:
                print(json.dumps({"phase": "extracting", "arm": arm}), flush=True)
                transport = client(root, arm, paid=True)
                system = (root / "learning/systems" / (arm + ".txt")).read_text()
                module_for(arm, system).update_cards(groups, root / "learning/seed.md", root / "learning/banks" / arm,
                    transport, workers=1, admit=transport.admit)
            write_json(root / "learning/completed.json", {"status": "awaiting_manual_candidate_review", "requests": 4})
            print("Extraction complete; actor calls remain gated on candidate review", flush=True)
        except Exception as error:
            write_json(root / "learning/stopped.json", {"type": type(error).__name__, "reason": str(error), "automatic_retry": False})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "check", "extract"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = prior.builder.output_root(args.output)
    {"prepare": prepare, "check": check, "extract": extract}[args.phase](root)


if __name__ == "__main__":
    main()

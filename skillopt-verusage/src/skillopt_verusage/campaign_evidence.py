"""Train-only complete evidence, frozen checkpoint selection, and exact card banks."""
from __future__ import annotations

from collections import Counter
import hashlib
import difflib
import json
from pathlib import Path
import re

from verus_self_evolve.proof_progress import (
    align_tool_calls_to_output_tokens, extract_verifier_calls, function_body,
    greedy_prune_proof_lines, proof_line_coverage, regression_transitions, stagnation_segments,
)
from verus_self_evolve.proof_dependencies import scoped_line_coverage

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shared_strings(value, *, short_keys=False):
    """Losslessly intern repeated long strings; no trace or source omission."""
    counts = Counter()
    def visit(node):
        if isinstance(node, str) and len(node) >= (64 if short_keys else 512):
            counts[node] += 1
        elif isinstance(node, list):
            for part in node: visit(part)
        elif isinstance(node, dict):
            for part in node.values(): visit(part)
    visit(value)
    keys = {text: str(index) if short_keys else hashlib.sha256(text.encode()).hexdigest()
            for index, (text,n) in enumerate(counts.items()) if n > 1}
    def encode(node):
        if isinstance(node, str) and node in keys: return {"$text_ref": keys[node]}
        if isinstance(node, list): return [encode(x) for x in node]
        if isinstance(node, dict): return {k:encode(x) for k,x in node.items()}
        return node
    return {"encoding": "lossless-shared-strings-v1", "strings": {key:text for text,key in keys.items()},
            "value": encode(value), "instructions": "Replace each {$text_ref: key} recursively with strings[key]. All records are complete."}


def expand_strings(packet):
    def expand(node):
        if isinstance(node, dict) and set(node) == {"$text_ref"}: return packet["strings"][node["$text_ref"]]
        if isinstance(node, dict): return {k:expand(x) for k,x in node.items()}
        if isinstance(node, list): return [expand(x) for x in node]
        return node
    return expand(packet["value"])


def load_trace(directory: Path):
    events = [json.loads(x) for x in (directory/"agent_events.jsonl").read_text().splitlines() if x.strip()]
    snapshots = {}
    for path in sorted((directory/"snapshots").glob("*candidate.rs")):
        snapshots.setdefault(sha(path), path.read_text())
    # Independently validate every stored diff against its complete source snapshot.
    chain = [{"event_index":e["event_index"], **e["data"],
              "diff_content":(directory/e["data"]["diff"]).read_text()}
             for e in events if e.get("type")=="lifecycle" and e.get("data",{}).get("snapshot")]
    previous = ""
    for node in chain:
        current = (directory/node["snapshot"]).read_text()
        expected = "".join(difflib.unified_diff(previous.splitlines(keepends=True),
                           current.splitlines(keepends=True),
                           fromfile="previous-candidate.rs", tofile="candidate.rs"))
        if expected != node["diff_content"]:
            raise ValueError("Snapshot diff is not lossless")
        if hashlib.sha256(current.encode()).hexdigest() not in snapshots:
            raise ValueError("Snapshot hash mismatch")
        previous = current
    # The initial add-whole-file diff is exactly derivable from its baseline.
    # Avoid sending a second, plus-prefixed copy of a large source file.
    if chain:
        first = chain[0]
        baseline = (directory/first["snapshot"]).read_text()
        first["diff_content"] = {"encoding":"derived-initial-unified-diff-v1",
            "instructions":"Compute unified_diff([], baseline.splitlines(keepends=True), fromfile='previous-candidate.rs', tofile='candidate.rs'). All subsequent diffs are supplied verbatim."}
    else:
        raise ValueError("Complete evidence requires initial snapshot")
    raw = [json.loads(x) for x in (directory/"codex_events.raw.jsonl").read_text().splitlines() if x.strip()]
    canonical = lambda x: json.dumps(x, sort_keys=True)
    represented = {canonical(e["data"]["raw_codex_event"]) for e in events if "raw_codex_event" in e.get("data",{})}
    supplemental = [{"source_id":f"raw:{i+1}","record":e} for i,e in enumerate(raw) if canonical(e) not in represented]
    value = {"original_input":(directory/"workspace/input.rs").read_text(),
             "prompt":(directory/"prompt.txt").read_text(), "events":events, "supplemental_raw":supplemental,
             "snapshots": {"encoding":"complete-baseline-and-unified-diff-chain", "baseline":baseline,
                           "instructions":"The first node is baseline (its add-whole-file diff is derivable). Apply subsequent unified diffs to the preceding source in event order; unchanged boundaries have empty diffs. Each node records the full source hash.", "chain":chain},
             "final_source":(directory/"workspace/candidate.rs").read_text(),
             "result":json.loads((directory/"result.json").read_text())}
    refs = {f"event:{e['event_index']}" for e in events} | {f"snapshot:{x}" for x in snapshots}
    refs |= {e["source_id"] for e in supplemental} | {"final_validation", "original_task", "final_proof"}
    return value, sorted(refs), snapshots


def analyze_progress(trace, snapshots, ledger_rows, task_key, function_name, verify, verify_preservation,
                     *, function_occurrence=0, reference_pruning=None, reference_components=None):
    """Host-only pruned-proof progress; report candidates without choosing a policy."""
    report = {"metric":"pruned-target-proof-line-coverage-v1", "curve":[],
              "stagnation_segments":[], "regression_transitions":[],
              "selection_policy":"pending_design_review", "semantic_progress_claim":False}
    if not trace["result"]["hard"]:
        return {**report,"status":"no_verified_reference"}
    final = trace["final_source"]
    passed,output = verify(final)
    if not passed:
        raise ValueError("Final proof failed fresh verification")
    pruning = (reference_pruning if reference_pruning is not None else
               greedy_prune_proof_lines(trace["original_input"],final,function_name,verify,
                                       occurrence=function_occurrence))
    pruned = pruning["pruned_source"]
    passed,pruned_output = verify(pruned)
    if not passed:
        raise ValueError("Pruned final proof failed fresh verification")
    preserved,preservation_output = verify_preservation(trace["original_input"],pruned)
    if not preserved:
        raise ValueError("Pruned proof failed preservation")
    ledger = [row for row in ledger_rows if row.get("task_id")==task_key]
    if not ledger:
        raise ValueError("Missing source output-token ledger")
    alignment = align_tool_calls_to_output_tokens(trace["events"],ledger)
    reference_body = function_body(pruned,function_name,occurrence=function_occurrence)
    calls = extract_verifier_calls(trace["events"])
    if not calls:
        raise ValueError("No exact verifier calls for proof progress")
    curve = []
    for call in calls:
        digest = call["candidate_sha256"]
        source = snapshots.get(digest)
        if source is None or hashlib.sha256(source.encode()).hexdigest()!=digest:
            raise ValueError("Verifier call has no matching exact snapshot")
        tokens = (alignment["tool_call_output_tokens"].get(call["tool_call_id"])
                  if call["origin"]=="actor" else alignment["total_output_tokens"])
        if tokens is None:
            raise ValueError("Verifier call has no exact output-token alignment")
        coverage_error = None
        if reference_components is not None:
            coverage = scoped_line_coverage(source,pruned,reference_components)
            coverage_error = '; '.join(c['error'] for c in coverage['components'] if c.get('error')) or None
        else:
            try:
                coverage = proof_line_coverage(function_body(source,function_name,occurrence=function_occurrence),reference_body)
            except ValueError as error:
                # A recorded candidate can temporarily be an isolated probe, not the target task.
                coverage_error = str(error)
                coverage = {"coverage":None,"matched_final_lines":None,
                            "final_lines":proof_line_coverage(reference_body,reference_body)["final_lines"]}
        curve.append({**call,"checkpoint_sha256":digest,"cumulative_output_tokens":tokens,
                      "proof_coverage":coverage["coverage"],"matched_final_lines":coverage["matched_final_lines"],
                      "pruned_final_lines":coverage["final_lines"],"verifier_tier":call["verifier"]["tier_rank"],
                      "coverage_error":coverage_error})
        if reference_components is not None:
            curve[-1]['component_coverage'] = coverage['components']
            curve[-1]['target_proof_coverage'] = coverage['components'][0]['coverage']
    if reference_components is not None:
        report['metric'] = 'compiler-scoped-target-and-helper-line-coverage-v2'
    return {**report,"status":"analyzed","curve":curve,"pruned_source":pruned,"token_alignment":alignment["alignment"],
            "original_final_sha256":hashlib.sha256(final.encode()).hexdigest(),
            "reference_sha256":hashlib.sha256(pruned.encode()).hexdigest(),"pruning":pruning,
            "fresh_validation":{"original_verus":output,"pruned_verus":pruned_output,
                                "pruned_preservation":preservation_output},
            "stagnation_segments":stagnation_segments(curve),
            "regression_transitions":regression_transitions(curve)}


def fork_comparison(original, checkpoint, branch, hint):
    """Align real suffix alternatives; concatenation is an analysis view, not actor replay."""
    events = original["events"]
    matches = [i for i,event in enumerate(events) if event["event_index"]==checkpoint["event_index"]]
    if len(matches)!=1 or events[matches[0]].get("candidate_sha256")!=checkpoint["checkpoint_sha256"]:
        raise ValueError("Fork checkpoint does not match original event")
    if hint["hint"]["checkpoint_sha256"]!=checkpoint["checkpoint_sha256"]:
        raise ValueError("Hint checkpoint does not match original fork")
    if hashlib.sha256(branch["snapshots"]["baseline"].encode()).hexdigest()!=checkpoint["checkpoint_sha256"]:
        raise ValueError("Branch initial checkpoint does not match original fork")
    if branch["original_input"]!=original["original_input"]:
        raise ValueError("Branch original task does not match fork source")
    split = matches[0]+1
    prefix,suffix = events[:split],events[split:]
    return {"checkpoint":checkpoint,"hint":hint,"original_prefix":prefix,"original_suffix":suffix,
            "augmented_suffix":branch["events"],"augmented_trace":prefix+branch["events"],
            "original_result":original["result"],"augmented_result":branch["result"],
            "event_namespaces":{"prefix":"event:","original_suffix":"event:","augmented_suffix":"branch:event:"},
            "hint_boundary_after_original_event":checkpoint["event_index"],
            "cost_scope":"Shared prefix occurred once; compare suffix cost separately, do not charge it twice.",
            "comparison_targets":["hint content","fork state","changed actions","verifier outcomes","suffix convergence cost"]}


def packet_trace(trace):
    """Final code is already represented completely by the validated snapshot chain."""
    digest = hashlib.sha256(trace["final_source"].encode()).hexdigest()
    if trace["snapshots"]["chain"][-1]["candidate_sha256"] != digest:
        raise ValueError("Final source is not the final recorded snapshot")
    return {**trace,"final_source":{"encoding":"complete-snapshot-chain-reference-v1",
        "sha256":digest,"instructions":"The full final proof is the last source in snapshots.chain, reconstructed losslessly from baseline and all supplied diffs."}}


def audit_cards(proposal, source_id, permitted_refs, forbidden_names=()):
    if proposal.get("source_task") != source_id or not isinstance(proposal.get("cards"),list):
        raise ValueError("Card source contract mismatch")
    for card in proposal["cards"]:
        content=card.get("content", "")
        if not isinstance(content,str): raise ValueError("Card content must be a string")
        if not content or not content.strip(): raise ValueError("Card missing content")
        for label in ("Trigger","Action","Why","Validate","Avoid when"):
            if not re.search(r"\*\*"+label+r":\*\*\s*\S",content): raise ValueError(f"Card missing field {label}")
        if not card.get("evidence_refs") or not set(card["evidence_refs"])<=set(permitted_refs): raise ValueError("Unknown card evidence")
        if re.search(r"\b[0-9a-f]{20}\b|/home/|/zp_vegeta/|```|\bproof\s+fn\b",content): raise ValueError("Private/task/code content in card")
        if re.search(r"\b(?:assert|assume|admit)\s*\(|\b(?:choose|forall|exists)\s*\||==>",content):
            raise ValueError("Copied proof code/formula in card")
        if any(name and re.search(r"(?<!\w)"+re.escape(name)+r"(?!\w)",content)
               for name in forbidden_names): raise ValueError("Benchmark target name in card")
        for action in re.finditer(r"\b(?:add|introduce|insert|create)\b",content,re.I):
            negated = re.search(r"\b(?:do not|must not|should not|never|avoid)\s+$",content[:action.start()],re.I)
            if not negated and re.match(r".{0,80}\b(?:assume|admit|axiom|external_body)\b",content[action.end():],re.I|re.S):
                raise ValueError("Card recommends bypass")


def exact_bank(proposals):
    cards=[];provenance={};known={}
    for proposal in proposals:
        for card in proposal["cards"]:
            content=card["content"]
            digest=hashlib.sha256(content.encode()).hexdigest()
            if digest not in known:
                ident=f"card-{len(cards)+1:03d}";known[digest]=ident
                cards.append({"id":ident,"content":content});provenance[ident]=[]
            provenance[known[digest]].append({"source_task":proposal["source_task"],"evidence_refs":card["evidence_refs"],
                                           "limitations":card.get("limitations",[])})
    return {"schema_version":"stage-card-bank-v1","cards":cards},provenance


def evaluation_schedule(items, conditions, repetitions=2):
    # One whole repetition before the next; rotate conditions across tasks/repeats.
    return [[(repeat,conditions[(i+repeat+offset)%len(conditions)],item)
             for i,item in enumerate(items) for offset in range(len(conditions))]
            for repeat in range(repetitions)]

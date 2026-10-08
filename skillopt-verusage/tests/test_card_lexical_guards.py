"""Lexical false-positive repairs must retain provenance and trust boundaries."""
import copy

import pytest

from skillopt_verusage.campaign_evidence import audit_cards
from skillopt_verusage.native_card_update import audit_response


def card(action="Use the available premise to establish the missing obligation."):
    return {"content": "**Trigger:** An obligation lacks an explicit supporting fact.\n"
            "**Action:** " + action + "\n"
            "**Why:** Existing premises can justify the required conclusion.\n"
            "**Validate:** Run the verifier and preservation check.\n"
            "**Avoid when:** The needed premise is absent from the current model.",
            "evidence_refs": ["event:1"]}


def audit(action, forbidden=("deserialize",)):
    audit_cards({"source_task": "synthetic", "cards": [card(action)]},
                "synthetic", ["event:1"], forbidden)


@pytest.mark.parametrize("word", ["deserializer", "deserialization", "deserializers",
                                   "predeserialize", "deserialize_helper"])
def test_generic_subwords_are_not_exact_benchmark_target_names(word):
    audit("Inspect the " + word + " contract before choosing the proof route.")


@pytest.mark.parametrize("content,forbidden", [
    ("Inspect deserialize before proceeding.", "deserialize"),
    ("Inspect (deserialize), then verify.", "deserialize"),
    ("Use the lemma_deserialize_record declaration.", "lemma_deserialize_record"),
    ("Inspect crate::deserialize before proceeding.", "deserialize")])
def test_exact_full_identifier_and_punctuation_boundaries_still_reject(content, forbidden):
    with pytest.raises(ValueError, match="target name"):
        audit(content, (forbidden,))


@pytest.mark.parametrize("content", [
    "Copy proof fn repair_goal into the proof.",
    "Use assert(missing_fact).",
    "Use assume(missing_fact).",
    "Use admit().",
    "Use choose |value| selected(value).",
    "Use forall|value| property(value).",
    "Use exists |value| property(value).",
    "State left ==> right explicitly.",
    "Copy ```proof code```.",
    "Read /home/person/private-proof.rs.",
    "Read /zp_vegeta/scratch/private-proof.rs.",
    "Reuse task 0123456789abcdefabcd."])
def test_private_code_path_formula_and_task_leak_guards_remain_active(content):
    with pytest.raises(ValueError): audit(content)


@pytest.mark.parametrize("verb", ["add", "introduce", "insert", "create"])
@pytest.mark.parametrize("target", ["assume", "admit", "axiom", "external_body"])
def test_positive_new_trust_actions_still_reject(verb, target):
    with pytest.raises(ValueError, match="bypass"):
        audit(f"{verb.capitalize()} a new {target} to close the obligation.")


@pytest.mark.parametrize("prefix,verb", [("Do not", "add"), ("Must not", "introduce"),
    ("Should not", "insert"), ("Never", "create"), ("Avoid", "add")])
def test_explicitly_negated_new_trust_prohibitions_are_allowed(prefix, verb):
    audit(f"{prefix} {verb} a new axiom or assumption; use existing verified premises.")


@pytest.mark.parametrize("first,second", [
    ("Do not add a new axiom.", "Introduce an axiom to finish."),
    ("Never introduce external_body;", "add an axiom instead."),
    ("Must not insert assume;", "create external_body for the missing proof."),
    ("Should not create admit;", "insert assume in the failing branch."),
    ("Avoid add a new axiom;", "add another axiom to close the goal.")])
def test_a_negated_first_verb_never_masks_a_later_positive_bypass(first, second):
    with pytest.raises(ValueError, match="bypass"):
        audit(first + " " + second)


def test_missing_model_premise_is_not_itself_an_instruction_to_add_new_trust():
    audit("Check whether the existing model supplies the additional premise needed by this route; "
          "if not, choose another proof route without weakening the contract.")


def native_fixture():
    groups = []
    for task in ("one", "two"):
        tids = [f"task:{task}:{kind}" for kind in ("original", "cp1", "cp2", "cp3")]
        groups.append({"source_task": task, "trace_ids": tids,
                       "evidence_ids": [tid + "/event:1" for tid in tids], "forbidden_names": []})
    c = card(); c.update(evidence_refs=["task:one:cp1/event:1"], source_tasks=["one"],
                         limitations=["Synthetic observations do not establish causal efficacy."])
    response = {"trace_analyses": [{"trace_id": tid, "observation": "Compare this actual branch."}
                                  for group in groups for tid in group["trace_ids"]], "cards": [c]}
    return response, groups


def test_eight_trace_list_with_known_refs_remains_accepted():
    response, groups = native_fixture()
    audit_response(response, groups)


@pytest.mark.parametrize("event", [173, 179])
def test_batch008_unknown_event_refs_remain_rejected(event):
    response, groups = native_fixture()
    response["cards"][0]["evidence_refs"].append(f"task:one:original/event:{event}")
    with pytest.raises(ValueError, match="evidence"):
        audit_response(response, groups)


def test_batch008_dict_analyses_are_not_coerced_or_silently_repaired():
    response, groups = native_fixture()
    response["trace_analyses"] = {a["trace_id"]: a["observation"] for a in response["trace_analyses"]}
    before = copy.deepcopy(response)
    with pytest.raises(ValueError, match="every trace"):
        audit_response(response, groups)
    assert response == before


@pytest.mark.parametrize("change", ["missing", "duplicate", "unsupported_source"])
def test_lexical_relaxation_does_not_relax_trace_or_source_coverage(change):
    response, groups = native_fixture()
    if change == "missing": response["trace_analyses"].pop()
    elif change == "duplicate": response["trace_analyses"][-1] = copy.deepcopy(response["trace_analyses"][0])
    else: response["cards"][0]["source_tasks"] = ["two"]
    with pytest.raises(ValueError): audit_response(response, groups)

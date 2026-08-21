# Verus Memory Index, Retrieval Trigger, and Card Design: Round 1 Refinement

## 1. Revised Claim Boundary

The broad hybrid index is engineering substrate already covered in substantial
part by RAG-Verus, KVerus, Rango and LeanDojo/ReProver. The focused research
mechanism is:

> At every valid Verus checkpoint, build an invisible high-recall candidate
> pool; separately inject at most one replay-certified `invoke_lemma`
> transition card, or abstain. Attribute every oracle loss to coverage,
> candidate generation, tri-state filtering, ranking, injection, or use.

The first experiment does not test a universal Verus memory platform. It tests
whether verifier-grounded recall attribution plus selective action injection
is feasible and non-harmful.

## 2. Observable Failure Routing

Every checkpoint is first assigned one of three mechanically observable
classes:

```text
HARNESS_INVALID
  process result missing OR permission/transport failure
  OR candidate/diagnostic hash mismatch OR incomplete diagnostic

VERIFIER_RESOURCE_SYMPTOM
  valid hash-bound Verus result explicitly reports rlimit/timeout/resource use

SEMANTIC_PROOF_FAILURE
  valid hash-bound Verus result with a syntax, type, assertion,
  precondition, postcondition, invariant, trigger, or other proof diagnostic
```

`HARNESS_INVALID` never triggers proof-memory injection. A
`VERIFIER_RESOURCE_SYMPTOM` is not initially labeled a knowledge gap. It
receives one bounded controlled same-code probe, for example a predeclared
higher-resource rerun or quantifier-profiler run. Only a reproducible
proof-complexity diagnosis can enter a later decomposition/quantifier-memory
study; resource routing is out of the first `invoke_lemma` MVP.

Within `SEMANTIC_PROOF_FAILURE`, the local ATLAS vocabulary and official Verus
checklist are used as query facets, not as unvalidated gold labels:

```text
symbol/API and precondition applicability
assertion/postcondition bridge
quantifier/trigger
case split
loop establishment/preservation/exit
bounded arithmetic and casts
opaque/reveal/fuel/induction
container extensionality and representation bridge
state invariant and liveness/fairness
```

Behavioral events are tracked independently:

```text
NO_OP
UNCHANGED_CANDIDATE
STATE_FINGERPRINT_CHANGED
ERROR_FRONTIER_REDUCED
ERROR_FRONTIER_REGRESSED
UNSAFE_DIFF
REPEATED_EQUIVALENT_STATE
```

## 3. Two Executable Policies

### 3.1 Search policy

```text
search_policy(state):
    if state.checkpoint_valid is false:
        return []
    return union(
        exact_symbol_candidates(state),
        fts_candidates(state),
        accessible_dependency_candidates(state)
    )
```

For the MVP this runs invisibly after **every** complete,
candidate-hash-bound Verus checkpoint, including the initial unverified state.
The candidates and channel provenance are logged but not visible to the agent.
This defines the search-recall ceiling before attempting to optimize search
frequency.

Future search-cost policies may use deterministic events, agent requests,
uncertainty, or learned value-of-retrieval, but only after the always-search
ceiling is measured.

### 3.2 Injection policy

```text
injection_policy(state, candidates, budget):
    if state.route != SEMANTIC_PROOF_FAILURE:
        return ABSTAIN
    eligible = tri_state_filter(candidates)
    active = [c for c in eligible if c.status == "active"]
    if not positive_injection_evidence(state, active):
        return ABSTAIN
    return top_one(active)
```

Positive injection evidence for the MVP requires:

1. same frozen repository and compatible toolchain scope;
2. same normalized error family;
3. state fingerprint exact match or a predeclared unification rule;
4. fully-qualified lemma is analyzer-accessible;
5. binding is type-checked or marked `unknown`, never mechanically false;
6. replay evidence reproduces the target diagnostic delta;
7. no machine exclusion condition matches;
8. card status is `active`.

The policy injects zero or one transition card. `shadow` cards are retrieved
and scored but never injected. Premise signatures remain tool/search output
and are not additional cards in the MVP.

## 4. Trigger Alternatives

The word “trigger” should mean injection trigger in the first experiment:

### Policy A: Always inject

Inject the top active card at every semantic checkpoint. This is a high-use
baseline and harm stress test, not the recommended policy.

### Policy B: Deterministic verifier-state FSM

Inject on the first exact-matched semantic state, every full
state-fingerprint change, `NO_OP/UNCHANGED_CANDIDATE`, or two repetitions of
an equivalent state. Suppress and roll back on regression/unsafe events.

### Policy C: Agent self-trigger

Allow a typed `memory.request(missing_kind, symbols, obligation)` tool call.
This adds a manual path but cannot be the sole trigger because the model may
not recognize missing knowledge.

### Policy D: Learned marginal-utility router

Estimate:

```text
score(state, card) = P(benefit) - P(harm)
```

from paired retrieval/no-retrieval outcomes, under an explicit injection
budget. This is deferred until enough matched states exist; the threshold and
realized use rate must be audited on held-out data.

### Policy E: Hybrid

Deterministic mandatory events plus agent request plus a learned optional
router. This is the target architecture after the deterministic MVP.

Recommended sequence:

```text
MVP: always invisible search + deterministic injection/abstain
next: add agent request
later: learned utility router
```

## 5. Minimal MVP Index

### 5.1 Canonical tables

SQLite stores:

```text
symbols
  fq_name, kind, mode, visibility, typed signature,
  requires, ensures, module, source hash, commit, Verus version

dependencies
  src symbol, edge type, dst symbol

transitions
  pre-state hash/fingerprint, post-state hash/fingerprint,
  added invoke_lemma action, diagnostic delta, replay result, safety result

cards
  minimal transition-card payload and status
```

### 5.2 Three candidate channels

1. exact name/signature/compiler-suggestion lookup;
2. FTS5/BM25 over fully-qualified names, signatures, specifications and
   normalized diagnostics;
3. analyzer-derived accessible dependency traversal.

Use a fixed per-channel quota, union and deduplication. Exact and
compiler-suggested hits occupy the highest priority bucket. FTS and graph ranks
may use reciprocal-rank fusion within a lower bucket. Structural fingerprint,
dense retrieval, generic proof-card types and a graph database are deferred.

### 5.3 Coverage invariants

The frozen index can mechanically guarantee:

1. every analyzer-resolved declaration appears exactly once in the symbol
   catalog;
2. every extracted explicit dependency edge round-trips;
3. every active/shadow card has a source hash, transition record and index
   projection;
4. no stale commit/version row is silently considered current.

These are index-completeness guarantees, not a guarantee that every useful
strategy is known.

## 6. Tri-State Compatibility and Filter Audit

Each predicate returns:

```text
VALID | INVALID | UNKNOWN
```

Only mechanically proven `INVALID` candidates are rejected. `UNKNOWN`
candidates survive in a quarantined pool and are logged; they may be injected
only if the MVP policy's predeclared rules allow that field to remain unknown.

Examples:

- inaccessible fully-qualified symbol: `INVALID`;
- analyzer proves incompatible arity/type: `INVALID`;
- associated type or generic unification unresolved: `UNKNOWN`;
- required precondition not currently visible but possibly provable:
  `UNKNOWN`, not invalid;
- wrong frozen repository commit: `INVALID`;
- stable repository card from a different Verus patch version: type-specific
  version rule, not universal invalidation.

Split the prior `negative_scope`:

```text
exclusion_conditions
  machine predicates under which this card is inapplicable

safety_constraints
  edits that remain forbidden if the card is used
```

Safety policy is enforced globally and cannot depend on retrieving an
anti-pattern card.

For every oracle candidate, log:

```text
filter_name, input_state, output_state, reason, oracle_member
```

Report both per-filter oracle loss and leave-one-filter-out rescue rate.

## 7. Mechanically Constructible Oracle Sets

Oracle construction applies only to high-fidelity source transitions:

1. exact immutable pre/post code hashes;
2. exact candidate-hash-bound pre/post Verus diagnostics;
3. exactly one proof-only edit interval;
4. extract every added fully-qualified lemma invocation;
5. replay the full edit on the immutable pre-state;
6. ablate each invocation/action atom and rerun Verus/Lynette;
7. instantiate each surviving candidate action independently where possible;
8. place every card that independently reproduces the predeclared target
   diagnostic delta and safety result in the equivalent oracle set.

The denominator for offline trigger/filter recall contains only states with at
least one replay-certified oracle member. Other states remain in live
end-to-end evaluation but do not receive invented retrieval labels.

The exact-action oracle is isolated:

- never indexed by the method arm;
- never used for ranking thresholds;
- never exposed in normal held-out prompts;
- only used as a diagnostic upper bound.

## 8. Recall Funnel

For oracle-labeled states:

```text
R0 Coverage:
  any oracle member exists in the frozen card inventory

R1 Search recall:
  any oracle member appears in the invisible candidate union

R2 Filter survival:
  any oracle member is not INVALID

R3 Rank recall@K:
  any oracle member is in the eligible top-K

R4 Injection recall:
  an oracle member is the injected top-one

R5 Use/effect:
  the instantiated action reproduces improvement in the current run
```

Compute conditional and end-to-end rates directly; do not multiply marginal
rates as if independent. Every missed state receives exactly one earliest-loss
label. Search recall is evaluated at multiple fixed per-channel budgets.

Additional diagnostics:

- alpha-renamed identifier perturbation;
- diagnostic-wording perturbation;
- inaccessible/wrong-direction/unmet-precondition/stale-version hard
  negatives;
- channel ablations;
- leave-one-filter-out rescue;
- realized search and injection rates;
- injected tokens and latency;
- paired retrieval benefit, neutral and harm rates.

## 9. Minimal Transition Card

Canonical storage is versioned JSON/JSONL; agent injection is a deterministic
short rendering.

```json
{
  "schema_version": "0.1",
  "card_id": "invoke-lemma-0001",
  "card_type": "invoke_lemma_transition",
  "status": "shadow",
  "scope": {
    "repo_id": "frozen-repo",
    "commit_sha": "<sha>",
    "verus_version_rule": "exact"
  },
  "state_fingerprint": {
    "error_family": "assertion_failure",
    "diagnostic_span_hash": "<hash>",
    "target_decl_hash": "<hash>",
    "local_spec_hash": "<hash>"
  },
  "lemma": {
    "fq_name": "crate::module::lemma_name",
    "signature": "proof fn lemma_name(...)",
    "requires": ["..."],
    "ensures": ["..."]
  },
  "action": {
    "binding_template": {"formal": "<typed-state-expression>"},
    "insertion_anchor": "<proof-span-id>"
  },
  "exclusion_conditions": [
    {"field": "mode", "op": "not_in", "value": ["proof"]}
  ],
  "safety_constraints": [
    "no_spec_edit",
    "no_exec_edit",
    "no_assume_admit_external_body_axiom"
  ],
  "evidence": {
    "pre_state_hash": "<hash>",
    "post_state_hash": "<hash>",
    "replay_id": "<id>",
    "replay_delta": {"target_error_removed": true},
    "lynette": "pass"
  }
}
```

Injected rendering:

```text
[invoke-lemma-0001]
WHEN: current assertion state matches the certified fingerprint.
DO: invoke crate::module::lemma_name with the shown typed binding at <anchor>.
EXPECT: remove the target assertion error.
DO NOT: edit spec/exec code or use proof bypasses.
```

Evidence histories, matched utility, parent lineage and lifecycle mutations are
stored in separate ledgers and deferred from the card core.

## 10. Falsifiable Evaluation

Frozen paired arms:

1. H0: no memory instrumentation;
2. always-search/no-injection: tests invisible instrumentation overhead;
3. selective top-one injection/abstain;
4. always top-one injection: harm/use stress test;
5. isolated exact-action oracle upper bound.

Primary:

- strict Verus + Lynette success;
- Expected Cost to Success;
- unsafe and regression rate.

Mechanism:

- earliest recall-loss stage;
- injection benefit/neutral/harm;
- injection and abstention rates;
- prompt-token and search latency costs.

Kill condition: if selective injection does not improve strict utility over H0
and no-injection controls without a safety regression, stop the skill-system
claim. Retain the static index only as engineering infrastructure.

## 11. Direct Answers to the Open Decisions

1. **Initial lookup:** always search invisible static premises at the initial
   valid checkpoint; do not inject a strategy card without certified evidence.
2. **Plateau:** use full state fingerprint and error-frontier delta, not only
   equal diagnostic text. Add `NO_OP/UNCHANGED_CANDIDATE` as immediate events.
3. **Anti-pattern:** safety checks bypass retrieval and are mandatory globally;
   recovery guidance may be a later card, but safety cannot depend on top-k.
4. **Storage:** SQLite + FTS5 + adjacency tables are sufficient for the MVP.
   A dedicated graph database is not justified.

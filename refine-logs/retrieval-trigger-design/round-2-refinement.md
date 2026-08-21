# Verus Memory Index, Retrieval Trigger, and Card Design: Round 2 Refinement

## 1. Final Focused Mechanism

The first system tests one narrow mechanism:

> Search a frozen bank of train-derived `invoke_lemma` transition cards after
> every valid Verus checkpoint, keep search invisible, and inject at most one
> validation-promoted card under a deterministic policy. On evaluation states,
> measure transfer opportunity and every recall loss against train-bank cards
> that independently replay successfully on that state.

Exact/FTS/dependency retrieval is reused substrate. The focused contribution,
if the experiment succeeds, is verifier-grounded earliest-loss attribution
plus selective replay-certified injection with an explicit abstain path.

## 2. Leakage-Safe Data and Execution Order

Freeze task- and near-code-disjoint partitions before card extraction:

```text
D_train
  readable by extraction and source-replay stages
  produces frozen B_train cards in status=shadow

D_val
  readable by deterministic binding/replay and promotion
  produces frozen B_active subset and freezes normalization, filtering,
  ranking, injection and binding-enumeration rules

D_eval
  readable only after all above artifacts are content-hash frozen
  measures normal live arms and offline recall
  never updates cards, active status, rankers, filters, normalization,
  unification, binding order or thresholds
```

Execution order on `D_eval`:

1. run H0, always-search/no-injection, selective-injection and always-injection
   live arms using frozen `B_active` and policies;
2. seal their logs and hashes;
3. construct the offline train-bank oracle by exhaustive replay of frozen
   `B_train` on immutable eval pre-states;
4. run the withheld exact-action ceiling in a separate workspace;
5. compute recall and end-to-end reports without feeding any oracle result
   back into a live arm.

The withheld eval transition, reference proof and exact action are invisible
to all normal arms and all train/validation decisions.

## 3. Observable Routing and Two Policies

The checkpoint router remains:

```text
HARNESS_INVALID
VERIFIER_RESOURCE_SYMPTOM
SEMANTIC_PROOF_FAILURE
```

Missing/permission/transport/stale-hash/incomplete diagnostics are
`HARNESS_INVALID` and never receive proof memory. A valid Verus rlimit/timeout
is `VERIFIER_RESOURCE_SYMPTOM` and is outside this lemma MVP. All other valid
hash-bound verifier failures are `SEMANTIC_PROOF_FAILURE`.

Behavioral events are separately logged:

```text
NO_OP
UNCHANGED_CANDIDATE
STATE_FINGERPRINT_CHANGED
FRONTIER_STRICTLY_IMPROVED
FRONTIER_REGRESSED
UNSAFE_DIFF
REPEATED_EQUIVALENT_STATE
```

Two independent functions and ledgers:

```text
search_policy(state, B_train) -> candidate_card_ids
injection_policy(state, candidate_card_ids, B_active) -> card_id | ABSTAIN
```

`search_policy` runs invisibly at every valid checkpoint, including the first
Verus result. `injection_policy` injects at most one active card or abstains.

## 4. Frozen Train Card Bank and Promotion

### 4.1 Source extraction

Only exact, immutable, candidate-hash-bound, proof-only transitions with an
extractable added fully-qualified `invoke_lemma` action are admitted.
Replaying the source action must reproduce the complete normalized
pre-to-post diagnostic frontier and pass Lynette. Such a card enters
`B_train` as `shadow`; source replay alone never makes it active.

### 4.2 Diagnostic frontier

Represent a frontier as a multiset of:

```text
(severity, normalized_error_family, target_decl_shape,
 diagnostic_span_AST_shape)
```

For this conservative MVP, a useful transition is:

```text
strict Verus+Lynette success
OR
post_frontier is a strict multiset subset of pre_frontier
```

No new normalized diagnostic is allowed. This deliberately excludes
error-swapping transitions that may be useful in a broader multi-step system.

### 4.3 Deterministic binding

Given a card and state, the binder:

1. enumerates analyzer-visible expressions by source order;
2. matches formal parameters by resolved Verus type and mode;
3. applies only normalization and alias rules frozen on `D_train`;
4. orders multiple bindings lexicographically by formal name then source span;
5. tests at most a predeclared fixed number per card/state.

A binding result is `VALID`, `INVALID` or `UNKNOWN`. `UNKNOWN` remains visible
for search/filter audits but is never injectable in the MVP.

### 4.4 `shadow -> active` on validation only

For every `shadow` card, exhaustively bind and replay it on its predeclared
in-scope `D_val` states. Promotion is lexicographic:

1. zero Lynette/spec/exec/bypass regression;
2. zero diagnostic-frontier regression;
3. at least one non-source validation state with strict success or strict
   frontier-subset improvement;
4. zero harmful validation replay among all mechanically valid bindings;
5. cost is only a tiebreaker.

Cards without a mechanically valid validation opportunity remain `shadow`.
For the small pilot, this is a deterministic promotion rule, not statistical
risk calibration.

## 5. Provenance Identity Versus Transfer Fingerprint

Never use raw task hashes as task-disjoint retrieval features.

```text
provenance_identity
  source repo/commit/path/span
  raw pre/post code and diagnostic hashes
  replay and Lynette record IDs

retrieval_fingerprint
  alpha-normalized diagnostic AST shape
  normalized target declaration/spec shapes
  error family
  required accessible-symbol signature
  proof/spec/exec mode

action_anchor_rule
  structural rule such as:
  before_failing_assertion
  proof_block_entry
  before_postcondition_boundary
```

All alpha-normalization, spec-shape extraction, equivalence and anchor rules
are defined and content-hash frozen after `D_val`, before `D_eval` is read.
Injection requires a resolved structural anchor and mechanically `VALID`
binding. Raw provenance fields are for auditing only.

## 6. Search Index and Card Projection

The search unit is always `card_id`.

Canonical SQLite tables:

```text
symbols
dependencies
transitions
cards
card_symbol_projection(card_id, lemma_symbol_id)
card_state_projection(card_id, error_family, target_shape, spec_shape)
```

Candidate channels:

1. **Exact:** exact lemma/compiler-suggested symbol hit, then join
   `symbol_id -> card_symbol_projection -> card_id`.
2. **FTS5:** index card retrieval projections directly: fully-qualified lemma
   name, signature, requires/ensures, error family and normalized state facets.
3. **Accessible dependency:** traverse analyzer-derived accessible symbol
   neighbors, then join each symbol to card IDs.

Every channel emits:

```text
substrate_hits
projected_card_ids
rank_within_channel
projection_reason
```

Fixed per-channel quotas are unioned and card IDs deduplicated. Exact hits form
the highest priority bucket; FTS/dependency ranks use fixed reciprocal-rank
fusion below it. A symbol hit is never counted as an oracle-card hit unless the
correct card ID survives the explicit projection.

Coverage invariants test all analyzer declarations, explicit edges,
card-symbol/state projections, source hashes and current-version constraints.

## 7. Train-Bank Oracle on Evaluation States

Let:

```text
B_train
  all frozen cards extracted only from D_train

U_eval
  all high-fidelity D_eval pre-states with a withheld replayable exact action

O_train(s)
  {c in B_train |
     deterministic_bind(c, s) has at least one VALID binding
     AND replay(c, binding, s) yields strict Verus+Lynette success
         or a strict diagnostic-frontier subset
     AND introduces no safety or frontier regression}
```

For the 10-20-card pilot, construct `O_train(s)` by exhaustive replay of every
in-scope train card and every binding allowed by the frozen finite enumerator.
This computation is independent of the retriever.

Do not use either invalid oracle:

- the withheld eval exact action as normal retrieval ground truth;
- only successfully retrieved candidates as the oracle pool.

The withheld exact action is an isolated ceiling only.

## 8. Recall Contract

Report over all `U_eval`:

```text
R-1 Transfer opportunity
  fraction of states with nonempty O_train(s)

End-to-end earliest loss
  NO_TRAIN_ORACLE | INDEX_COVERAGE | CANDIDATE_GENERATION |
  FILTER | RANK | INJECTION | USE_EFFECT
```

Conditional on nonempty `O_train(s)`:

```text
R0 Coverage:
  any O_train(s) member exists in the indexed frozen B_train projection

R1 Search recall:
  any oracle card ID appears in the invisible union

R2 Filter survival:
  any oracle member remains VALID or UNKNOWN

R3 Injectable survival:
  any oracle member is VALID, resolved-anchor and active

R4 Rank recall@K:
  any injectable oracle member is top-K

R5 Injection recall:
  the injected top-one belongs to O_train(s)

R6 Live effect:
  the action reproduces a useful transition in the live run
```

`UNKNOWN` protects search/filter audit recall but is not included in
injectable recall. Compute conditional and end-to-end counts directly. Report
the `R-1` denominator prominently so good conditional recall cannot hide
almost-zero transferable coverage.

Required audits:

- fixed per-channel budget sweep;
- alpha-renaming and diagnostic-wording perturbations;
- inaccessible, wrong-direction, unmet-precondition and stale-version hard
  negatives;
- per-filter oracle loss;
- leave-one-filter-out rescue;
- channel ablations;
- search/injection rate, tokens and latency;
- paired injection benefit/neutral/harm.

## 9. Minimal Card

```json
{
  "schema_version": "0.1",
  "card_id": "invoke-lemma-0001",
  "card_type": "invoke_lemma_transition",
  "status": "shadow",
  "provenance_identity": {
    "repo_id": "<repo>",
    "commit_sha": "<sha>",
    "source_path": "<path>",
    "pre_state_hash": "<hash>",
    "post_state_hash": "<hash>",
    "source_replay_id": "<id>"
  },
  "retrieval_fingerprint": {
    "error_family": "assertion_failure",
    "diagnostic_ast_shape": "<alpha-normalized-shape>",
    "target_decl_shape": "<normalized-shape>",
    "local_spec_shape": "<normalized-shape>",
    "required_symbol_signature": "<signature>"
  },
  "lemma": {
    "fq_name": "crate::module::lemma_name",
    "signature": "proof fn lemma_name(...)",
    "requires": ["..."],
    "ensures": ["..."]
  },
  "action": {
    "binding_rule_id": "typed-source-order-v1",
    "anchor_rule": "before_failing_assertion"
  },
  "exclusion_conditions": [
    {"field": "mode", "op": "not_in", "value": ["proof"]}
  ],
  "safety_constraints": [
    "no_spec_edit",
    "no_exec_edit",
    "no_assume_admit_external_body_axiom"
  ],
  "activation": {
    "status": "shadow",
    "validation_policy_id": "strict-frontier-subset-v1",
    "validation_evidence_ids": []
  }
}
```

Detailed per-run evidence and utility stay in separate ledgers. The agent sees
only the deterministic rendering:

```text
[card_id]
WHEN: <matched normalized state>
DO: invoke <fully-qualified lemma> with <resolved typed binding>
AT: <resolved structural anchor>
EXPECT: remove a frontier diagnostic without adding one.
DO NOT: edit spec/exec code or use proof bypasses.
```

## 10. Injection Trigger Policies

The research MVP uses always-invisible-search plus deterministic injection.
The injection FSM reacts to:

- first valid exact/unified semantic-state match;
- any normalized full-state-fingerprint change, even inside one error family;
- `NO_OP` or `UNCHANGED_CANDIDATE`;
- two `REPEATED_EQUIVALENT_STATE` events;
- regression/unsafe event, which forces rollback and `ABSTAIN`.

Agent self-request is a later secondary path. A learned
`P(benefit)-P(harm)` router is deferred until matched data exists. The target
production design is a hybrid, but neither later trigger enters the MVP claim.

## 11. Evaluation and Kill Gate

Frozen live arms:

1. H0;
2. always-search/no-injection;
3. deterministic selective injection/abstain;
4. always top-one active-card injection;
5. isolated withheld exact-action ceiling.

Primary outcomes:

- strict Verus + Lynette success;
- Expected Cost to Success;
- unsafe and diagnostic-frontier regression.

Mechanism outcomes:

- `R-1`, R0-R6 and earliest loss;
- active-card coverage;
- injection benefit/neutral/harm;
- realized search/injection budget;
- context tokens and search latency.

If selective injection does not improve strict utility over H0 and
no-injection without safety/frontier regression, stop the skill-system claim.
The index may remain as engineering infrastructure.

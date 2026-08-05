# Round 2 Independent Review

## Verdict

The revision materially fixes the architectural overreach of Round 0. Always
invisible search, separate search/injection policies, observable resource
routing, a single `invoke_lemma` card type, and the reduced three-channel index
are now credible implementation choices.

It is nevertheless **not implementation-ready**. The central recall
experiment still has an oracle-definition leak: once the withheld eval
transition's exact action is isolated, the proposal does not define recall
ground truth strictly in terms of the frozen train card bank. In addition,
source-state replay is currently sufficient evidence for an `active` card in
the injection policy, but the proposal never defines a leakage-safe
`shadow -> active` promotion gate. This can promote cards that merely swap one
error for another or that work only on their source state.

**Verdict: REVISE**

## Scores

The eight dimensions remain equally weighted.

| Dimension | Round 2 score | Assessment |
|---|---:|---|
| Problem anchoring | 9.5 | The claim is now narrow: recall attribution plus selective injection, not a universal memory platform. |
| Failure-pattern coverage | 8.5 | Harness, verifier-resource, semantic, and behavioral states are cleanly separated; ATLAS is correctly used only as facets. |
| Index/recall design | 7.0 | The funnel is much clearer, but the candidate unit alternates between symbols and cards, and the train-bank oracle denominator is unresolved. |
| Trigger design | 7.5 | Always-search removes search-trigger misses and the FSM now governs injection; active-card evidence and transferable state matching remain underspecified. |
| Memory-card schema | 7.0 | The card is substantially smaller, but raw hashes/source anchors are mixed with transferable query fields and no activation evidence is stored. |
| Evaluation falsifiability | 6.5 | Arms and kill condition are strong, but oracle construction, split boundaries, and promotion can leak eval transitions or select an artificially easy denominator. |
| MVP simplicity | 8.0 | One action family, three channels, SQLite, top-one injection, and deferred learned routing are appropriately scoped. |
| Novelty boundary | 7.5 | Prior substrate is explicitly acknowledged; verifier-grounded earliest-loss attribution plus selective replay-certified injection is a plausible focused systems claim. |

**Overall score: 7.69 / 10**

The score increase reflects real simplification, not round number. It remains
below 9 because the proposed recall result cannot yet be interpreted without
oracle and promotion leakage.

## Prior Blocker Audit

| Prior blocker | Status | Review |
|---|---|---|
| Always invisible search | **RESOLVED** | Search runs at every valid hash-bound Verus checkpoint and remains invisible to the solver. |
| Two executable policies | **MOSTLY RESOLVED** | Interfaces and logs are separate, but `positive_injection_evidence` depends on an undefined activation/promotion contract. |
| Tri-state filtering | **PARTIAL** | `VALID/INVALID/UNKNOWN` and filter audits are correct, but the proposal still allows an unknown binding to be injected under unspecified “predeclared rules.” |
| Oracle sets | **PARTIAL / BLOCKING** | Replay and ablation are defined, but the oracle set is not explicitly restricted to frozen `D_train` cards evaluated on `D_eval` pre-states. |
| Resource routing | **RESOLVED** | Resource symptoms are separated from harness failure and excluded from the first lemma MVP. |
| Minimal card/MVP | **MOSTLY RESOLVED** | Scope is appropriate; transferable fingerprints, anchors, and active status still require repair. |

## Blocking Issues

### 1. CRITICAL — Recall oracle must come from the frozen train card bank

The withheld eval transition's exact-action card cannot define normal recall:
it contains the answer and is correctly isolated as a ceiling. After that
isolation, the proposal needs the following explicit definition.

Let:

```text
B_train
  = cards extracted only from D_train transitions and frozen before eval

U_eval
  = all high-fidelity D_eval pre-states with a withheld replayable exact action

O_train(s)
  = {c in B_train |
       deterministic_bind(c, s) succeeds
       AND replay(c, s) reproduces the predeclared useful delta
       AND introduces no safety or error-frontier regression}
```

For the 10-20-card MVP, `O_train(s)` should be constructed by exhaustive replay
of every in-scope train card on each eval pre-state, independent of the
retriever. A bounded deterministic enumeration may be used when a card has
multiple type-correct bindings, but its bound and ordering must be frozen.

The recall contract then becomes:

```text
R-1 Transfer opportunity:
  fraction of U_eval with nonempty O_train(s)

R0-R5:
  conditional recall funnel on states with nonempty O_train(s)

End-to-end recall:
  earliest-loss rates over all U_eval, including no-train-oracle states
```

This avoids two invalid alternatives:

1. defining the oracle from the held-out exact action, which leaks the answer;
2. defining the oracle only among retrieved candidates, which makes recall
   circular.

The withheld exact action remains a separate ceiling arm only. It must not
enter `B_train`, card activation, ranking, unification-rule design, or recall
denominators.

### 2. CRITICAL — No leakage-safe `shadow -> active` promotion gate

The injection policy uses only `active` cards, but the revision never states
how a replay-certified source card becomes active. Source replay establishes
action attribution on the source state; it does not establish transfer or
non-harm.

Freeze three disjoint partitions:

```text
D_train: extract cards and source replay evidence
D_val:   bind/replay cards and decide shadow -> active
D_eval:  measure recall and live effects; never change cards or policies
```

Promotion must be lexicographic:

1. zero Lynette/spec/exec/bypass regression;
2. no global error-frontier regression;
3. strict success, or a predeclared target reduction with no new/harder
   verifier diagnostic;
4. only then use cost as a tiebreaker.

The example `replay_delta: {"target_error_removed": true}` is insufficient.
Local evidence already shows that removing a `PostCondFail` can introduce a
persistent `AssertFail`. Record the complete normalized pre/post diagnostic
frontier and require non-regression. If the pilot is too small to justify
task-disjoint activation, keep all cards `shadow` and evaluate oracle/search
mechanics only; do not silently equate source replay with active utility.

### 3. CRITICAL — Transferable query fields are mixed with source identity

The card uses:

```text
diagnostic_span_hash
target_decl_hash
local_spec_hash
insertion_anchor: <proof-span-id>
```

Exact raw hashes and source span IDs will usually match only the source task.
Relaxing them post hoc through an unspecified “predeclared unification rule”
creates an exact-task leakage and researcher-degree-of-freedom risk.

Separate:

```text
provenance_identity:
  raw source hashes and original span IDs

retrieval_fingerprint:
  frozen alpha-normalized diagnostic AST shape
  normalized target/spec shape
  required accessible-symbol signature

action_anchor_rule:
  a transferable structural location such as
  before_failing_assertion or proof_block_entry
```

Define and freeze normalization/unification before `D_eval` is read. Raw hashes
may validate provenance but must not be retrieval keys for task-disjoint
claims. The MVP should not inject a card with an `UNKNOWN` binding or anchor:
retain it for filter-recall audit, but require mechanically type-checked
bindings and a resolved structural insertion anchor for injection.

### 4. IMPORTANT — Search must return card IDs, not an ambiguous symbol/card mix

`search_policy` currently unions exact symbols, FTS records, and accessible
dependencies, while the recall funnel asks whether an oracle **card** appears
in the pool. Specify a deterministic projection:

```text
channel hit symbol/diagnostic
  -> join to B_train cards by lemma FQ name and indexed state facets
  -> candidate card IDs
  -> deduplicate cards
```

Log both the substrate hit and the resulting card projection. Otherwise a
lemma can be counted as retrieved even when the actionable transition card
was never generated, or the same lemma's wrong-state card can be counted as an
oracle hit.

## New Leakage and False-Negative Risks

1. **Oracle-constructibility selection bias:** reporting R1-R5 only on states
   with a replayable card can hide that almost no eval state has a transferable
   train card. `R-1` and end-to-end rates are mandatory.
2. **Unknown-binding injection:** tri-state recall protection is useful, but
   allowing unresolved bindings into injection converts a recall fix into a
   safety/precision leak. Unknowns should survive search, not MVP injection.
3. **Post-hoc unification:** target/spec hash relaxation chosen after seeing
   held-out cases can encode the evaluation task. All normalization rules must
   be frozen using `D_train/D_val`.
4. **Error swapping:** target-error removal plus Lynette pass is not proof
   progress. Full diagnostic-frontier non-regression is required.
5. **Oracle execution leakage:** exhaustive train-card replay on `D_eval`
   creates labels for evaluation only. Its results must not update active
   status, ranking, filters, bindings, or subsequent live runs.

## Complexity Check

The current MVP is no longer obviously overbuilt. SQLite, three candidate
channels, top-one injection, five diagnostic arms, and deferred learned
routing are defensible. The future agent-request and learned-router sections
are acceptable as explicitly deferred context, but should not enter the first
implementation or paper claim.

No new model, dense index, graph database, anti-pattern card family, or
additional trigger should be added in the next revision. The only necessary
changes are contracts for data splits, train-bank oracle construction,
activation, transferable fingerprints, and card projection.

## Minimum Revision to Reach Implementation Readiness

1. Freeze `D_train/D_val/D_eval` and state exactly which artifacts each phase
   may read.
2. Define `O_train(s)` by exhaustive deterministic binding and replay of
   frozen train cards on eval pre-states; add `R-1` transfer opportunity.
3. Keep withheld eval exact actions only in an isolated ceiling arm.
4. Define `shadow -> active` on `D_val` with global diagnostic-frontier and
   safety non-regression; never promote on `D_eval`.
5. Separate raw provenance hashes from normalized retrieval fingerprints and
   replace source span IDs with structural anchor rules.
6. Require resolved/type-checked bindings for injection; keep `UNKNOWN`
   candidates search-visible but non-injectable.
7. Make every search channel return card IDs through an explicit,
   logged symbol-to-card projection.

After these changes, the plan can plausibly exceed 9 as an
implementation-ready, falsifiable systems mechanism study. Without them,
high recall or selective-injection gains would remain vulnerable to
denominator selection, held-out action leakage, and source-state overfitting.


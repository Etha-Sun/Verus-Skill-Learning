# Round 3 Final Independent Review

## Final Verdict

**READY**

The proposal is now implementation-ready as a narrow, falsifiable systems
mechanism study. The Round 2 blockers have been resolved in substance rather
than hidden behind broader architecture:

- data partitions and read order are explicit and leakage-safe;
- the method card bank and active subset are frozen before `D_eval`;
- `O_train(s)` is defined exclusively from frozen train cards replayed on eval
  pre-states, independent of retrieval;
- withheld eval actions are isolated as a ceiling;
- source replay and validation promotion have separate roles;
- full diagnostic-frontier non-regression prevents error swapping;
- raw provenance is separated from transferable retrieval features;
- only mechanically valid bindings and resolved anchors are injectable;
- search channels explicitly project substrate hits to card IDs;
- `R-1` exposes how often transferable train memory exists before conditional
  recall is reported.

This verdict means the experiment may be implemented. It does not pre-judge
that selective injection will improve live Verus repair or that the eventual
result will support a top-venue paper.

## Scores

The eight dimensions are equally weighted.

| Dimension | Score | Final assessment |
|---|---:|---|
| Problem anchoring | 9.5 | The proposal tests one precise bottleneck: whether train-derived lemma transitions can be found, safely selected, and locally useful without unconditional context injection. |
| Failure-pattern coverage | 9.0 | Harness, verifier-resource, semantic, and behavioral outcomes are mechanically separated; the conservative one-family MVP appropriately excludes ambiguous resource cases. |
| Index/recall design | 9.2 | Card IDs are the retrieval unit, channel projection is explicit, oracle construction is retriever-independent, and earliest-loss attribution is complete. |
| Trigger design | 9.0 | Always-invisible search removes search-trigger false negatives; a deterministic top-one injection/abstain policy handles state changes, no-ops, repetition, and regression. |
| Memory-card schema | 9.0 | The single typed card is minimal, machine-renderable, provenance-safe, and separates action applicability, safety, activation, and evidence. |
| Evaluation falsifiability | 9.2 | Frozen splits, an isolated ceiling, `R-1`, end-to-end loss labels, matched arms, frontier regression, and a hard kill condition make failure interpretable. |
| MVP simplicity | 9.2 | One action family, SQLite, three channels, deterministic binding, one injected card, and no learned router are the smallest adequate mechanism. |
| Novelty boundary | 8.4 | The proposal honestly treats hybrid retrieval and adaptive retrieval as prior substrate; novelty is a focused verifier-grounded attribution and selective-injection protocol, whose research value remains conditional on results. |

**Overall score: 9.06 / 10**

## Round 2 Blocker Audit

### 1. `D_train / D_val / D_eval` freeze and execution order

**RESOLVED.**

`D_train` alone creates `B_train`; `D_val` alone determines `B_active` and
freezes all policies; normal `D_eval` live arms run before offline oracle
construction; oracle results cannot update any live arm. The withheld action
and reference proof are explicitly invisible to normal arms.

### 2. Train-bank definition of `O_train(s)`

**RESOLVED.**

The proposal defines:

```text
O_train(s) = train cards with a VALID deterministic binding whose
             independent replay on eval pre-state s gives strict success
             or a strict frontier subset without safety/frontier regression
```

For the small pilot, every in-scope train card and every binding permitted by
the frozen finite enumerator is replayed. The retriever cannot determine its
own oracle, and the eval exact action cannot inflate ordinary recall.

### 3. `shadow -> active` promotion

**RESOLVED.**

Source replay produces only `shadow` cards. Promotion requires a non-source
`D_val` improvement, zero harmful mechanically valid bindings, zero
safety/frontier regression, and never reads `D_eval`. This is correctly
described as a conservative deterministic gate rather than statistical risk
calibration.

### 4. Frontier non-regression

**RESOLVED.**

The normalized diagnostic frontier is a multiset, and a useful partial
transition must produce a strict subset with no new diagnostic. This
deliberately excludes potentially useful error-swapping transitions from the
first study and directly addresses the local evidence that target-error
removal can expose a persistent new error.

### 5. Provenance versus transfer fingerprint

**RESOLVED.**

Raw code/path/span hashes are audit-only. Retrieval uses alpha-normalized
diagnostic, declaration, specification, mode, and accessible-symbol shapes.
Structural anchor rules replace source span IDs, and all normalization and
equivalence rules are frozen before evaluation.

### 6. Valid binding and anchor

**RESOLVED.**

The finite binder has deterministic enumeration and a fixed cap. `UNKNOWN`
survives search/filter audits but is never injectable. Injection requires both
a mechanically `VALID` binding and a resolved structural anchor.

### 7. Symbol-to-card projection

**RESOLVED.**

Each channel emits substrate hits and projected card IDs through explicit
tables and reasons. A symbol hit cannot be counted as a card/oracle hit unless
the correct card ID survives the join and deduplication.

### 8. `R-1` selection-bias disclosure

**RESOLVED.**

Transfer opportunity is reported over all high-fidelity `U_eval`, followed by
end-to-end earliest loss. Conditional R0-R6 cannot hide a nearly empty set of
states for which train memory transfers.

## New Risk Audit

No new blocking trigger, filter, oracle, or leakage issue is apparent.

The following are non-blocking execution clarifications that should be frozen
in the experiment configuration and manifest:

1. Resolve the wording difference between rules “frozen on `D_train`” and
   rules “frozen after `D_val`”: author normalization/binding algorithms from
   `D_train`, tune only predeclared choices on `D_val`, then content-hash the
   final configuration before opening `D_eval`.
2. Define “in-scope `D_val` states” mechanically using immutable repository,
   action-family, error-family, and accessibility predicates; do not curate
   validation states after seeing replay outcomes.
3. Freeze deterministic tie-breaking after exact-bucket/RRF ranking, the
   binding cap, live repetition count, context budget, ECTS censoring rule, and
   rollback semantics.
4. Keep offline exhaustive replay results physically unavailable to normal
   live-arm workspaces, even though oracle construction occurs after their logs
   are sealed.

These are experiment-manifest details, not missing method components.

## Simplicity and Claim Boundary

No additional retrieval model, graph database, memory-card type, anti-pattern
router, or learned trigger should be added before the kill gate. The paper-level
claim should remain:

> In a frozen Verus setting, verifier-grounded train-card replay and selective
> top-one injection permit auditable transfer-opportunity and recall-loss
> measurement, and may improve strict live utility without unconditional
> memory toxicity.

If `R-1` is near zero, the result falsifies card transfer rather than merely
retriever quality. If `R-1` is adequate but R1-R4 are weak, the funnel
localizes the retrieval/promotion defect. If retrieval succeeds but live
utility does not, the skill-system claim stops. This makes the proposed MVP
both implementable and scientifically useful under positive or negative
outcomes.

## Blocking Issues

**NONE.**


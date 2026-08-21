# Round 1 Independent Review

## Overall Judgment

The proposal identifies the right engineering problem and has two strong design
choices: verifier/harness validity precedes proof-memory routing, and `SEARCH`
is conceptually separated from `INJECT`. However, the current design is not yet
evaluation-ready. Its main weakness is that trigger recall, hard-filter recall,
and the proposed oracle are not defined against the same mechanically
constructible ground truth. As a result, the system could report a strong
recall funnel while silently losing useful memory before search, at a hard
filter, or when converting a successful transition into a card.

The MVP is also broader than the evidence supports. One error family and exact
single-edit lemma transitions do not require seven retrieval views, five card
types, a general lifecycle model, parent lineage, utility aggregation, and
three injected cards. That breadth makes the proposal look like a general
Verus memory platform rather than the smallest experiment that tests whether
selective memory helps.

## Scores

Scores are equally weighted because no alternative weighting was specified.

| Dimension | Score | Review |
|---|---:|---|
| Problem anchoring | 9.0 | Directly targets trigger misses, retrieval loss, and context toxicity without claiming that all failures are knowledge failures. |
| Failure-pattern coverage | 6.5 | Broad and locally grounded, but the categories are not yet operational decision labels; `rlimit/timeout` remains partly mixed with semantic proof failure. |
| Index/recall design | 7.5 | The multi-channel union and R0-R7 funnel are strong, but binary hard gates can create unmeasured false negatives and the oracle unit is unstable. |
| Trigger design | 6.0 | The FSM is auditable, but it misses no-op/unchanged candidates and proof-state changes within one error family; search and injection are not yet two executable policies. |
| Memory-card schema | 5.5 | Canonical JSON is appropriate, but the schema is overdesigned for the MVP and conflates applicability exclusions with safety instructions. |
| Evaluation falsifiability | 6.0 | Useful baselines and live outcomes are present, but “smallest required card” is not a unique or mechanically available oracle, and the oracle arm risks held-out-answer leakage. |
| MVP simplicity | 5.0 | SQLite is sufficient, but the proposed indexes, card union, lifecycle, ranking, triggers, and five live arms exceed the smallest one-family lemma-transition test. |
| Novelty boundary | 5.5 | Most index and adaptive-retrieval elements are established; the potentially distinct claim is narrower than the current system description. |

**Overall score: 6.38 / 10**

**Verdict: REVISE**

The direction should not be rejected, but implementation should pause until the
trigger oracle, filter semantics, and MVP boundary are repaired.

## Evidence Check

### Local evidence

1. The R041 failure-path audit strongly supports `HARNESS_GATE`: all nine Qwen
   closest-failure logs had denied Verus calls, while the successful Codex path
   depended on iterative compiler feedback. This proves that missing verifier
   access must not be mislabeled as missing proof knowledge. It does not prove
   that the proposed semantic-failure taxonomy is an accurate router.
2. The ATLAS result supports vocabulary induction, not a ground-truth failure
   classifier. The taxonomy has no human gold labels; the Qwen/frontier
   comparison measured evidence grounding and actionability, not diagnostic
   accuracy. ATLAS codes therefore cannot serve as trigger labels without
   adjudication or mechanical routing predicates.
3. The local retrieval-skill evidence shows task-condition crossings and
   global-skill toxicity, which motivates selective retrieval. Most selected
   cells have one trajectory, while the repeated same-task gain remains within
   H0 variability. It does not yet provide card-level utility labels or a
   reliable learned-router training set.

### Closest-work boundary

- [RAG-Verus](https://arxiv.org/html/2502.05344v1) already describes code and
  summary retrieval, learned premise projection, and compiler-supported
  dependency-graph retrieval.
- [KVerus](https://arxiv.org/html/2605.03822v2) already combines typed metadata
  dependencies, semantic lemma indexing, versioned Verus knowledge, and
  diagnostic-driven refinement.
- [Rango](https://arxiv.org/html/2412.14063) retrieves project proofs and
  premises at every evolving proof step; state-adaptive retrieval is therefore
  not a new contribution.
- [LeanDojo/ReProver](https://arxiv.org/abs/2306.15626) already makes accessible
  premises and hard negatives central to formal retrieval.
- [Self-RAG](https://openreview.net/pdf?id=hSyW5go0v8) establishes that deciding
  when to retrieve and whether retrieved evidence is useful are distinct
  adaptive decisions outside formal verification.

Consequently, exact/FTS/graph/structural fusion, state-dependent retrieval, and
search timing are substrate. A defensible contribution would have to be the
joint, verifier-grounded mechanism for attributing recall loss and selectively
injecting replay-certified actions under an explicit no-memory option.

## Required Stress Tests

### 1. Trigger false negatives

The current mandatory FSM has three avoidable misses:

- A useful repository lemma may be required before a diagnostic-specific
  failure is observed; `G1` searches only exact/dependency context.
- The proof obligation may change while `error_family` and source span remain
  unchanged. The R041 prefix-to-offset-extensionality path is an example of
  meaningful progress within a broad assertion-failure family.
- An agent can return an unchanged candidate or make no proof action after a
  valid diagnostic. This is not covered until two equivalent failures satisfy
  `PLATEAU`.

For the MVP, run cheap high-recall search after every complete,
candidate-hash-bound verifier checkpoint, including the initial state. Let the
FSM govern **injection**, not whether an oracle can enter the candidate pool.
Add explicit `NO_OP/UNCHANGED_CANDIDATE` and full state-fingerprint-change
events. A later learned router may optimize search cost only after this
always-search recall ceiling is measured.

### 2. Hard-filter false negatives

The hard filters are unsafe as binary predicates:

- Rust/Verus generics, associated types, aliases, coercions, and unresolved
  preconditions can make compatibility `unknown`, not false.
- Exact version matching is appropriate for toolchain cards but too strict for
  some stable repository or proof-pattern cards.
- `negative_scope` currently mixes two meanings: “this card is inapplicable
  when X holds” and “if used, do not perform unsafe edit X.” Applying both as a
  hard exclusion can discard exactly the recovery card needed after an unsafe
  edit.
- `shadow` cards should be logged for evaluation but must not be injected as if
  active.

Use three-valued gates: `valid`, `invalid`, and `unknown`. Reject only proven
invalidity; retain unknown candidates in a quarantined pool for audit. Split
`negative_scope` into machine predicates `exclusion_conditions` and
non-negotiable `safety_constraints`. Report per-filter oracle loss and a
leave-one-filter-out rescue rate.

### 3. Search versus injection

The conceptual separation is correct but incomplete. The proposal needs two
explicit functions and two independent logs:

```text
search_policy(state) -> candidate pool, invisible to the solver
injection_policy(state, valid candidates, budget) -> zero or one card
```

`T1`-`T6` currently specify when to search but do not define the positive
evidence required for injection. “Zero-to-three” also creates unnecessary
attribution ambiguity. The MVP should inject at most one transition card;
premise signatures may be tool output rather than cards. The
always-search/no-injection arm is essential because it tests instrumentation
overhead without context steering.

### 4. Oracle and ground truth

“The smallest card/premise/action required” is not a unique ground truth.
There may be several valid lemmas, redundant calls, or different proof actions
that reproduce the same verifier delta. A successful edit also does not prove
that every referenced premise was necessary.

Construct **oracle sets**, not one smallest card:

1. restrict to exact single-edit, pre/post-hash-bound transitions;
2. mechanically extract added fully-qualified lemma invocations;
3. replay the edit on the saved pre-state;
4. ablate each invocation or action atom and rerun Verus/Lynette;
5. accept every card whose instantiated action independently reproduces the
   target delta as an equivalent oracle.

The held-out exact-action oracle may be used only as a diagnostic upper bound.
It must not enter the method index, ranking tuning, or normal test prompt.
States without a replay-certified oracle cannot contribute to trigger recall;
they remain live end-to-end evaluation cases.

### 5. Infrastructure, resource, and semantic routing

`SMT resource gap` should not be directly classified as
knowledge-addressable. Introduce three observable states:

```text
HARNESS_INVALID
VERIFIER_RESOURCE_SYMPTOM
SEMANTIC_PROOF_FAILURE
```

- Missing process result, transport timeout, permission denial, stale hash, or
  incomplete diagnostics is `HARNESS_INVALID`.
- A hash-bound Verus invocation that reports rlimit/timeout is initially
  `VERIFIER_RESOURCE_SYMPTOM`.
- Route that symptom to proof memory only after a bounded controlled probe,
  such as a same-code higher-resource rerun, shows that pure resource recovery
  is insufficient and the diagnostic is reproducible.

This prevents the R040/R041 infrastructure confounds from being counted as
retrieval opportunities while preserving genuine quantifier-explosion and
proof-decomposition cases.

## Blocking Issues

1. **CRITICAL — No mechanically stable oracle for trigger and filter recall.**
   Replace the single “smallest card” with replay/ablation-certified oracle
   sets and isolate the oracle upper-bound arm from the method index.
2. **CRITICAL — Search-trigger false negatives remain structurally possible.**
   Always run cheap search at every valid verifier checkpoint in the MVP; use
   the FSM as the injection gate and add no-op/state-fingerprint triggers.
3. **CRITICAL — Binary hard gates and `negative_scope` can remove useful
   candidates.** Add tri-state compatibility, card-type-specific version rules,
   shadow isolation, and separate exclusion predicates from safety constraints.
4. **IMPORTANT — Resource symptoms are not operationally separated from
   semantic proof failures.** Add the three-state routing contract and a
   controlled resource probe.
5. **IMPORTANT — The card/index design exceeds the MVP claim.** Reduce the
   first implementation to one transition-card type, one action family, and
   exact + FTS + accessible dependency retrieval.
6. **IMPORTANT — The novelty claim is implicit.** State explicitly that the
   broad Verus hybrid index and adaptive retrieval are reused substrate; test
   only verifier-grounded recall attribution plus selective action injection.

## Minimum Revision

The smallest adequate revision is:

1. Freeze one repository/version/error family and exact single-edit
   `invoke_lemma` transitions.
2. Store a minimal transition card:

   ```text
   id, scope, state_fingerprint, fq_lemma_signature,
   binding/insertion template, exclusion_conditions,
   safety_constraints, source hashes, replay evidence, status
   ```

3. Use exact symbol, FTS5, and analyzer-derived accessibility/dependency
   candidates only. Defer dense retrieval, generic structural fingerprints,
   five card types, parent lineage, aggregate utility, and graph databases.
4. Search invisibly after every valid verifier checkpoint; inject at most one
   active, replay-certified card using deterministic eligibility, otherwise
   abstain.
5. Evaluate the funnel against replay-certified oracle sets with
   leave-one-filter-out audits, then compare H0, always-search/no-injection,
   selective injection, always injection, and an isolated oracle upper bound.
6. Treat this run as a falsifiable systems mechanism study. If selective
   injection does not beat the static/no-injection controls without safety
   regression, retain the index as engineering infrastructure and stop the
   skill-system claim.


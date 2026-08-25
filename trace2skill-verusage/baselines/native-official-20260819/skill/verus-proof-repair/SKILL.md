---
name: verus-proof-repair
description: Repair incomplete or failing Verus proofs through verifier-guided iteration. Use when a Verus function, lemma, invariant, specification bridge, or arithmetic obligation does not verify.
---

# Verus Proof Repair

Use the current verifier state to make the smallest justified proof change.
This initial skill intentionally contains no task-specific proof mechanisms;
lower-frequency mechanisms may be added to `references/` from observed evidence.

## Core workflow

1. Run `verus` on the assigned target file before editing and reproduce the exact diagnostic; use an existing Verus log only as secondary evidence if a fresh run is not possible. Then read the failing function, its contracts, and that diagnostic. If the diagnostic is not a proof obligation (for example, unavailable `builtin_macros`, parser errors, or macro-delimiter errors), resolve that environment or macro failure before continuing.
2. State the exact unproved proposition and the facts visible at that point; expand the target definition and classify its logical structure before selecting a tactic. Classify the diagnostic before choosing an edit: parse/type errors may need syntax or cast fixes; proof failures require adding a missing proof fact or trigger fix, not cosmetic rearrangement of parentheses, literals, or casts. Run `verus --expand-errors` to locate the exact failing assertion.
3. Choose one small proof change that could expose the missing connection. Before choosing an induction or decomposition for a recursive combinator, inspect its actual definition (`assert ... by(compute_only)` or the vstd declaration) and align the proof structure with the real recursion direction; for example, `Seq::fold_left` recurses via `drop_last`/`last`, not first-element. Before introducing a new lemma or macro, search the surrounding source and installed vstd for an existing proof construct whose shape matches the obligation; reuse it with the exact predicates from the failing definition.
4. Edit only the proof-relevant code. Use the exact target file path named by the task and patch that file in place. If a separate proof-only annotated copy is used for isolated validation, keep the original unchanged until the copy verifies, preserving specifications and executable code, and then apply the proof annotations back to the assigned target file; do not create or verify a separate `_verified.rs` copy as the deliverable unless the repository/task explicitly assigns that artifact. Run Verus on the same assigned target path again, filtering output for `verified`, `errors`, or `aborting`.
5. Use the changed diagnostic to decide the next step; do not stack unrelated changes.
If macro expansion or code generation is unavoidable, use a deterministic tool and immediately validate the expected generated items before verification. Avoid ad-hoc line-skipping or brace-counting scripts; they silently drop or duplicate blocks.
6. Apply fixes in the requested source file in place. Finish only after a fresh Verus run on the assigned proof target — normally the original target file, or a separate `_verified.rs` copy only when the repository/task explicitly assigns that artifact — succeeds with zero errors, the proof-only safety check passes, and a final audit of the edited target confirms no newly added forbidden constructs (`assume`, `admit`, `external_body`, axioms) remain and the verified-function count matches the obligations changed. A run that reports only automatic trigger notes has succeeded; add the suggested `#![auto]` annotation and re-verify for a clean final run. A pass on a `*_verified.rs` or macro-expanded copy does not satisfy the task unless that copy is the assigned proof target.

If syntax, proof mode, or an API signature is uncertain, inspect the local Verus
guide or installed vstd declaration before editing.


## New Section

## Proof construction and gap checks

- Every proof block must change the proof state. Use at least one concrete step (`reveal`, `assert`, `compute`, a lemma call, or a definition unfold) in every `assert ... by { ... }`, proof-function body, or lemma body; comments and empty `by {}` blocks do not establish facts.
- Proof commands must add verifier facts; comments do not. Replace each comment of the form "X follows" with an `assert`, `assert ... by`, `reveal`, or lemma call that establishes X.
- Inspect the exact preconditions of any proof lemma before calling it. Prove each named precondition with its own verified assertion or helper lemma before the call. If a call fails on a precondition mismatch, derive the required facts from visible hypotheses; do not delete the lemma unless it is genuinely irrelevant. Before invoking a proof lemma or macro, prove every `requires` clause in preceding assertions. If Verus reports `precondition not satisfied`, locate the emitted condition and prove it from current hypotheses; comments and empty `by {}` blocks add no facts.
- If a `requires` fact seems out of scope, assert that exact fact in the problematic context before declaring a Verus limitation; the usual cause is missing unfolding or quantifier instantiation.
- When a lemma conclusion and the goal differ only by predicate arrangement, prove the intermediate entailment explicitly with assertions or temporal-logic lemmas. Comments, semantic-equivalence claims, or an adjacent lemma call do not discharge the goal.
- Keep state-level and temporal-level reasoning separate. A state-level `forall` cannot directly consume an `always(lift_state(P))` temporal hypothesis; prove the state-level implication first, then lift it into the temporal entailment with the appropriate rule.
- For temporal or higher-order obligations, unfold `entails`, `valid`, `always`, and `lift_state` into explicit quantifier facts and assert the expanded fact for arbitrary executions/positions.
- Do not add unsupported syntax (e.g., trigger annotations on lambdas, `broadcast use`) without checking the local guide first.
- Fix the first failing assertion locally; do not rewrite the entire proof or switch strategies until the first failure is understood and a local fix has been tried. Continue while Verus still reports the target postcondition error; a proof body made of comments and a lemma call is incomplete until a fresh Verus run succeeds.
## Safety boundaries

- Preserve executable behavior and existing function contracts. Add only proof annotations, specifications, invariants, lemmas, and assertions; do not rewrite macros, trait implementations, or data definitions.
- Never add `assume`, `admit`, `#[verifier(external_body)]`, `#[verifier(external_fn_specification)]`, axiom-like definitions or ad hoc axioms for definitional facts, `unimplemented!()` proof bodies, empty-bodied `proof fn`/`#[verifier::ext_equal]` proof functions, or any verification bypass, even as a temporary experiment. In particular, do not introduce a trusted `external_body` helper with `ensures false` to discharge unreachable branches; prove them from preconditions, invariants, or match conditions instead. Ordinary proof functions must verify their own `ensures`.
- Do not claim success from narration, a smaller error count, or verification of a copy/generated artifact (e.g., a `_verified.rs` sidecar) instead of the requested target file. Before declaring completion, confirm the final verification command uses the target path, the target file contains the proof-relevant changes, and no newly added forbidden constructs (`external_body`, `unimplemented!`, `assume`, `admit`, or axiom markers) remain.
- If macro expansion or transformation is needed, apply the resulting content back into the original target file and verify that path; do not create a corrected copy or manually expand macros to make a proof pass.
- Before introducing a new helper lemma for an unproved library or opaque-function fact, search vstd and the current crate for existing verified lemmas or permitted reveal/unfold rules, and try to prove the fact in a `by` block first.
- Never comment out or delete assertions required by a later proof call.
- After finding a proof, apply the annotations to the assigned target file and verify the original path unless the repository or task explicitly assigns a separate copy as the proof target.
- If a separate `<name>_verified.rs` workspace is used for isolated validation, keep the original unchanged, run `grep -E "(admit|assume|external_body)"` and a signature/contract `diff -u` against the target, then apply the proof-only changes back to the assigned target path; do not treat the verified copy as the deliverable unless it is the assigned proof target.
- Keep broadly applicable procedure here. Put detailed, lower-frequency
  mechanisms in directly linked `references/*.md` files and read them only when
  their observable trigger matches the current obligation.


## New Section

## Reference patterns

Known reusable proof patterns live in `references/`. Read the linked file before editing when the observable trigger matches:

- General macro/env, init, empty-container, loop, equality/iff, and early-return obligations: [General Verus proof patterns](references/proof-patterns.md).
- Temporal stability, stable conjunctions, and bounded universal stability postconditions: [Temporal stability proof patterns](references/temporal-stability-proofs.md).
- Temporal and execution logic, `entails`/`leads_to`/`tla_exists`, quantified temporal triggers, temporal predicate equality, suffix rewriting, and higher-order temporal proofs: [Temporal and execution proof patterns](references/temporal-logic-proofs.md).
- Set equality, set/map membership, sorted no-duplicate set removal, recursive finite-set properties, and finite-set fold/map equality: [Set proof patterns](references/set-proof-patterns.md).
- Struct equality that depends on function-field equality: [Function extensional equality](references/function-extensional-equality.md).
- Length-prefixed serialization, primitive encoding length, and serialization lemma preconditions: [Serialization proof patterns](references/serialization-proof-patterns.md).
- `always(lift_state(P))` invariants and state-machine transition preservation: [State-machine invariant proof patterns](references/state-machine-invariants.md).
- `filtered.len() == 0` and empty-filtered-multiset equivalence: [Multiset length-zero proof patterns](references/multiset-length-zero-proofs.md).
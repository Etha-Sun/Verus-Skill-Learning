---
name: verus-proof-repair
description: Actor-visible baseline for Verus proof tasks. It covers broad procedural knowledge for reproducing and localizing exact failing obligations, classifying the missing bridge, deriving facts from definitions and existing verified lemmas, selecting and testing the smallest justified mechanism, interpreting changed diagnostics, and performing final proof-only exact-target acceptance. Narrow or low-frequency mechanisms with exact names and project-specific contracts remain outside this root. All content is candidate_unvalidated until a separate held-out gate evaluates it.
---

# Verus proof repair baseline: localize, ground, classify, test, and stop

## Core procedures

### Reproduce and localize the exact failing obligation before editing

**When:** A Verus proof task is stalled or failing; the exact unproved assertion, precondition, postcondition, proof body, or parse/type location is not yet isolated.

1. Run the verifier on the unmodified source or exact task-specified target and save the original diagnostic.
2. Read any available verifier log and identify the first or exact reported item: assertion, body, postcondition, precondition, parse/type error, or macro/environment error.
3. Restate the exact failing item locally in the context where it must be proved; do not begin global rewrites.
4. If the report is vague, use expanded diagnostics or a minimal in-place assertion to expose the precise obligation.

**Check:** The exact failing item can be named and restated without guessing; subsequent edits target that item rather than unrelated proof structure.

### Classify the failure before choosing a repair mechanism

**When:** A reproduced diagnostic is available and before any structural or cosmetic edit is made.

1. Separate parse/type errors from proof-failure errors; syntax/literal/cast/parenthesis edits are only justified for parse/type errors.
2. Separate environment/macro/generated-code failures from logical proof failures when diagnostics never reach a proof obligation.
3. For proof failures, classify the missing bridge: definitional unfolding, existing verified lemma/precondition, trigger or quantifier instantiation, recursive induction, temporal stability/entailment, state-level transition fact, container membership/cardinality, sequence equality, exact witness/ghost value, or exact-target artifact gap.
4. Record the chosen class; after each change, compare the new diagnostic against it.

**Check:** The chosen repair class matches the diagnostic; cosmetic surface edits and whole-proof restructuring are not used for proof-failure obligations.

### Ground the obligation from actual definitions, existing verified lemmas, and explicit proof steps

**When:** The failure is a missing logical fact or inert definitional/temporal fact, not a parse/type or trusted-policy exception.

1. Inspect the actual definition of the relevant function or combinator with `assert ... by(compute_only)`, `reveal`, `unfold`, or existing equational lemmas before choosing induction/decomposition.
2. Search for already verified lemmas whose ensures/postconditions directly support the needed equality, length, membership, fold, or state-transition fact.
3. Before invoking any lemma or macro, inspect its requires clauses and prove each missing precondition with explicit assertions or small helper derivations.
4. Replace comment-only proof blocks with actual proof terms: `assert`, `assert ... by`, lemma calls, local `let` facts, induction, or explicit forall assertions.
5. Rerun after grounding; do not introduce empty `ext_equal` proofs, `external_body` proof functions with `unimplemented!()`, or equivalent trusted shortcuts.

**Check:** The verifier accepts the previously missing fact via a visible definitional step, verified lemma, or explicit proof term; no new trusted axiom or unimplemented proof-function body is present.

### Choose and test the smallest justified mechanism for the classified bridge

**When:** After localization and grounding, one specific narrow bridge remains; the mechanism must match the classified failure.

1. Select the smallest local repair: a single target assertion, lemma call, trigger adjustment, witness extraction, stable/entailment composition, induction step, container equality direction, sequence equality split, or exact constructive ghost value.
2. Keep executable code, specifications, signatures, trait implementations, and macro-bearing source unchanged unless the task explicitly permits that class of edit.
3. Make one localized change instead of deleting the callee, rewriting the whole proof, or expanding macros unnecessarily.
4. Run the verifier on the exact target after that change.

**Check:** The change is proof-only or task-permitted; the target diagnostic advances, disappears, or changes to a new precise obligation.

### Interpret the changed diagnostic and reclassify or stop

**When:** After each localized change, especially when the same first failure persists or the diagnostic changes unexpectedly.

1. If the same first failing assertion remains, do not repeat the same repair or start a broad rewrite; return to the exact reported item.
2. If the diagnostic advances to a new obligation, keep the proven prefix and classify the new missing bridge independently.
3. Recheck the selected mechanism against the evidence: if a trigger placement is rejected, a lemma/macro is absent, arity/constructor form does not match, or a state-level fact is not derivable, abandon that mechanism.
4. Use a minimal in-context probe before claiming a limitation such as a `requires` fact being out of scope or a numeric/definitional fact being unsupported.
5. Stop or reclassify when continuing would require introducing trust, changing executable behavior/specs beyond policy, or looping without a changed diagnostic.

**Check:** Decisions to continue, reclassify, or stop are based on a changed diagnostic or a confirmed missing prerequisite, not on repeated opaque attempts or assumed limitations.

### Final proof-only audit, exact-target verification, and trust-boundary review

**When:** A candidate solution is complete or near-final, before declaring success.

1. Diff the original against the proposed artifact and reject non-proof-annotation edits unless explicitly authorized.
2. Search for `admit`, `assume`, `external_body`, `unimplemented`, and empty or axiom-like `ext_equal` proof declarations; treat a textual hit as an audit trigger, not automatic rejection if existing external executable specifications are explicitly permitted by policy.
3. Keep existing external executable specifications and their trust boundary unchanged; do not extend the boundary or claim their facts were newly proved by the verifier.
4. For exact-target tasks, verify the task-specified source path, not a generated or sidecar copy, unless a separate verified-copy convention is explicitly permitted and final policy is satisfied.
5. Run the exact-target verifier command once; repeat the exact command only for a final reproducibility audit or when the first result may be transient or environment-dependent.

**Check:** The diff is proof-only; no forbidden trusted shortcut or bypass is introduced; exact target verifies; trust boundaries are preserved, not extended, and success claims match actual file content.

## Safety and stopping rules

- Preserve executable behavior, specifications, contracts, signatures, trait implementations, macro-bearing source, and data definitions; proof changes must be proof-only or explicitly task-permitted.
- Prohibit assumptions, admits, verifier bypasses, and any newly introduced trusted helper used to discharge the target obligation.
- Do not categorically ban every declaration carrying `#[verifier::ext_equal]` or `#[verifier::external_body]`; existing external executable specifications explicitly permitted by project policy are not themselves a repair failure.
- Forbid introducing or relying on empty or axiom-like `ext_equal` proof declarations, `external_body` proof functions with `unimplemented!()`, or equivalent trusted shortcuts to bypass the target proof.
- Preserve existing external executable specifications; do not extend their trust boundary and do not claim their facts were newly verifier-proved.
- A textual grep hit for `admit`, `assume`, `external_body`, `unimplemented`, or empty `ext_equal` is an audit trigger, not by itself a rejection reason.
- Require verifier feedback after the smallest justified change; stop or reclassify when evidence contradicts the selected mechanism.
- One successful exact-target verifier run is the normal acceptance check; do not mandate an unconditional second full verifier run after every success. Repeat the exact command only for a final reproducibility audit or when the first result may be transient or environment-dependent.
- All knowledge remains candidate_unvalidated until the separate held-out gate evaluates it.
- Do not conclude a Verus limitation from repeated failure without a minimal in-context probe; do not insert assumptions or empty proof bodies as a way to satisfy the verifier.

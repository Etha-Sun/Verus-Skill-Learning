# VeruSAGE Executive Skill

Repair only proof and ghost code. Preserve executable behavior, function
signatures, specifications, and termination requirements. Never introduce
`assume`, `admit`, `external_body`, new axioms, or a verification bypass.

Use the current Verus diagnostic as the primary signal. Before editing, classify
the failure (precondition, postcondition, invariant entry/exit, quantifier,
arithmetic, type/mode/scope, or termination), inspect the implicated context,
and choose the narrowest matching VeruSAGE action. Prefer an existing lemma or a
small local assertion over duplicating a proof. Re-run Verus after a meaningful
change; if the same failure repeats, change the proof strategy rather than
repeating the same edit. Accept a candidate only when Verus verifies it and the
proof-only safety comparison passes.

## On-demand proof repair references

An optional reference library is available in this workspace. The complete
index below lists every reference's title, applicability cues, and file link.
You decide whether, when, and which references to read based on your current
proof state; no retrieval ranking or fixed reference count is imposed.
Read any indexed reference by ID:

    python3 reference_read.py compound-stability-existing-rules

You may read additional references, decline their advice, or continue without
them. Check Trigger and Avoid when against the current state, perform required
prechecks, and use normal verification and preservation tools after acting.
References are fallible advice, not proof. Briefly identify a consulted
reference's ID and why it applies or why you decline it in your progress
message. Do not bulk-read the library or modify library files. Reading is
optional and uses the normal task time and context budget.

Index descriptions are routing cues only. Read the full Trigger and Avoid when
of the relevant rule before acting. A reference may contain several conditional
rules; selecting it does not make every rule applicable. Cross-links point to
related rules under their stated conditions, not mandatory next steps.

## Reference index

- [compound-stability-existing-rules](references/compound-stability-existing-rules.md): Stable compound temporal predicate such as conjunction of always-lifted components.
- [direct-existing-lemma-bridge](references/direct-existing-lemma-bridge.md): Goal matches an already-declared library lemma or trait bridge whose premises are available.
- [eventual-witness-index-bridge](references/eventual-witness-index-bridge.md): Eventual/existential temporal goal with known occurrence or witness.
- [existing-roundtrip-proof-mode](references/existing-roundtrip-proof-mode.md): Deserializer/constructor success branch returns value not connected to input.
- [final-liveness-helper-chain](references/final-liveness-helper-chain.md): Final liveness theorem needing invariant, stability, base liveness, phase descent, condition unpacking.
- [finite-set-fold-cardinality-induction](references/finite-set-fold-cardinality-induction.md): Fold over finite set with finiteness/equality goal.
- [function-field-projection-syntax](references/function-field-projection-syntax.md): Compile/type error using call-like dot syntax on function-valued field or field like method.
- [ghost-empty-witness](references/ghost-empty-witness.md): Ghost aggregate/history field must be empty.
- [leads-to-transitivity-existing-helpers](references/leads-to-transitivity-existing-helpers.md): Lead-to transitivity conclusion.
- [library-broadcast-activation](references/library-broadcast-activation.md): Pointwise proof stuck on installed library operation.
- [loop-termination-and-invariants](references/loop-termination-and-invariants.md): While loop lacks decreases or loop-body facts disappear.
- [natural-integer-type-mismatch](references/natural-integer-type-mismatch.md): Type error from natural subtraction used as natural, natural length as integer index, or empty sequence lacking element type.
- [nondeterministic-step-result](references/nondeterministic-step-result.md): Machine result equals transition of manually chosen step but step not unique.
- [opaque-conversion-avoid-extraction](references/opaque-conversion-avoid-extraction.md): Ghost extraction through uninterpreted conversion unwrap triggers failed precondition.
- [opaque-spec-function-facts](references/opaque-spec-function-facts.md): Need length/body/equality fact about closed/opaque/nondecreasing spec function.
- [phase-accumulation-bridge](references/phase-accumulation-bridge.md): Phase-descent lemma uses recursive next-phase while base liveness concludes all-phase bundle.
- [post-verification-cleanup](references/post-verification-cleanup.md): Verification already successful; only remaining issue is proof-only safety comparison difference or low-confidence auto-trigger warning.
- [predicate-equality-mutual-entailment](references/predicate-equality-mutual-entailment.md): Equality between logical predicates such as predicate and its conjunction with entailed predicate.
- [proof-helper-qualified-path](references/proof-helper-qualified-path.md): Proof helper/macro out of scope and top-level import would survive deghosting.
- [quantified-proof-antecedent-binder-scope](references/quantified-proof-antecedent-binder-scope.md): Inside a quantified implication, antecedent not assumed or binder shadowed.
- [record-function-field-equality](references/record-function-field-equality.md): Record equality involving function-valued fields.
- [sequence-extensional-equality](references/sequence-extensional-equality.md): Sequence equality direct assertion fails.
- [sequence-fold-concat-equality](references/sequence-fold-concat-equality.md): Fold over concatenated sequences equals concatenation of folds.
- [set-equality-membership-witness](references/set-equality-membership-witness.md): Set/image equality with no direct lemma.
- [specialized-fold-bound-lemmas](references/specialized-fold-bound-lemmas.md): Generic fold lemmas do not connect to concrete fold expressions.
- [specialized-temporal-action-binder-type](references/specialized-temporal-action-binder-type.md): Fairness/action specialized to fixed controller leaves residual payload type mismatch.
- [temporal-entailment-pointwise-lifting](references/temporal-entailment-pointwise-lifting.md): Entailment/leads-to over cluster states/suffixes body empty or final postcondition unproved.
- [temporal-existential-witness-lifting](references/temporal-existential-witness-lifting.md): Leads-to/equality with existential message/state predicates.
- [temporal-induction-natural-offset](references/temporal-induction-natural-offset.md): Property at arbitrary natural suffix index.
- [temporal-predicate-equality-pointwise](references/temporal-predicate-equality-pointwise.md): Equality of temporal/spec-level function objects such as universal/always/nested applications.
- [temporal-suffix-shift-helper](references/temporal-suffix-shift-helper.md): Suffix/always-derived goal where existing accepted unfolding/shift helper matches.
- [transition-system-step-safety](references/transition-system-step-safety.md): Invariant/preservation/safety goal over finite state machine transitions.
- [trigger-inference-annotation](references/trigger-inference-annotation.md): Active Verus trigger inference failure for quantifier/choose/witness.
- [universal-equivalence-pointwise](references/universal-equivalence-pointwise.md): Equivalence between two universal formulas with different bodies.
- [universal-instantiation-concrete](references/universal-instantiation-concrete.md): Universal fact in scope not used at needed concrete index/execution/term.
- [view-equality-constructor-case](references/view-equality-constructor-case.md): Equal abstract views imply equal marshalability with no packaged bridge.
- [weak-fairness-pointwise-lemmas](references/weak-fairness-pointwise-lemmas.md): Top-level weak fairness/leads-to not closing.

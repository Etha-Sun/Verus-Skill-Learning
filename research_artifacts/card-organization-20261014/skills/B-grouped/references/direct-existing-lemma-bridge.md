# Direct reuse of an existing lemma or trait bridge

## Scope

- Consult when: Goal is a known property about library types or structured view equality
- Consult when: An installed or already-declared lemma/trait contract has matching conclusion and available premises
- Not for: No matching lemma or extra premises are unavailable
- Not for: Equality form cannot connect to current postcondition
- Not for: Manual constructor case is required because bridge is insufficient

## Rules

- [Direct reuse of an installed library lemma matching the proof obligation](#installed-library-lemma-direct)
- [Original card-003](#original-card-003)
- [Original card-043](#original-card-043)

<a id="installed-library-lemma-direct"></a>
## Direct reuse of an installed library lemma matching the proof obligation

Source cards: card-001

**Trigger:** A proof obligation is a known algebraic property about library types, such as mapping over a union of sets, and an installed library already provides a lemma whose conclusion matches that obligation.
**Action:** Before constructing a manual case analysis, inspect the installed library definitions for a lemma with the same conclusion. If one exists, invoke that lemma in the proof body with arguments matching the current obligation and let the verifier close the postcondition.
**Why:** Existing verified library lemmas have already handled witness extraction and extensional reasoning. Reusing such a lemma is narrower and faster than re-proving the same property. In the observed set-image union task, every continuation that selected the direct library lemma verified on the first attempt.
**Validate:** Run the verifier and confirm zero errors; run the proof-safety comparison and confirm it passes. Check that only the proof body changed and no signatures or specifications were modified.
**Avoid when:** The installed library has no lemma matching the goal, the lemma requires additional premises not currently available, or the lemma uses an equality form that the verifier cannot connect to the present postcondition.

<a id="original-card-003"></a>
## Original card-003

Source cards: card-003

**Trigger:** A proof obligation asks to show that two structured values have equal views under assumptions that both values are marshalable and their serialized representations are equal; an existing trait or generated instance already promises view equality under those assumptions.
**Action:** Invoke the existing proof method whose contract maps marshalability and equal serialization to view equality. If needed, expose the view-equal relation and assert the required structural view equality so the open view-specification definitions can unfold. If the solver still cannot close the structural equality, case-split on the constructors and propagate field equalities.
**Why:** The trait-level proof is already trusted background and corresponds exactly to the function premises. The generated view equality and view definitions are open, so once the relation is exposed, structural view equality can be derived by definitional unfolding without inventing a new assumption.
**Validate:** Run the verifier and confirm zero errors; run the proof-safety comparison and confirm it passes. Ensure only the proof body changed and no specifications or executable behavior were modified.
**Avoid when:** The trait method or generated instance is unavailable in the current source, or the view-equal relation does not logically imply the structural view equality for the particular type. Do not weaken the specification or add a trusted body if the relation is insufficient.

<a id="original-card-043"></a>
## Original card-043

Source cards: card-043

**Trigger:** A proof function has an empty body and must show that two datatype values with equal abstract views have equal marshalability predicates.
**Action:** First try the narrowest existing route: invoke a declared specification lemma that equates abstract view equality with the type's custom view-equal predicate; explicitly assert that custom relation for the two values; then invoke the trait lemma whose premise is that relation and whose conclusion contains marshalability equality. Only if that chain does not discharge the obligation, expand the two values by constructor cases. For matching constructors derive each field's view equality and use the corresponding per-field equal-view and equal-serialization lemma; for mismatched constructors derive a contradiction from their distinct view forms.
**Why:** Existing declarations already package the mathematical fact, so using them avoids duplicating structural definitions and may be accepted without enumerating constructors. The fallback case analysis is still useful when the solver cannot instantiate the packaged equivalence.
**Validate:** Run the checker and look for one verified function and zero errors. Then run the proof-only comparison; success is no difference output.
**Avoid when:** If the view-equal specification lemma exists only as an opaque declaration and cannot be instantiated with the terms in scope, do not keep repeating the same call; switch to the explicit constructor case analysis and prove the field-level premises directly. Also avoid weakening the postcondition or adding assumptions to make the chain pass.

- Distinguish from [set-equality-membership-witness](set-equality-membership-witness.md): Use this route only when the existing lemma itself closes the algebraic goal; otherwise set equality requires membership extensionality and explicit witnesses.

- Distinguish from [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque-spec route needs an open counterpart/connector or fixed-width lemma, not a direct goal-matching lemma.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Use this route only when the existing lemma itself closes the algebraic goal; otherwise set equality requires membership extensionality and explicit witnesses.

- Related [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque-spec route needs an open counterpart/connector or fixed-width lemma, not a direct goal-matching lemma.

- Related [view-equality-constructor-case](view-equality-constructor-case.md): Direct bridge first tries packaged declaration/trait route; this family is the fallback explicit case analysis.

- Related [library-broadcast-activation](library-broadcast-activation.md): Direct bridge invokes a matching lemma; broadcast route explicitly brings a trusted axiom group into proof scope for case analysis.

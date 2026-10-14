# Direct reuse of an existing lemma or trait bridge

## Scope

- Consult when: A library lemma matches an algebraic goal, or the goal connects serialization, view equality, and marshalability
- Consult when: The selected direct route has a matching installed/declared lemma or trait contract with available premises
- Not for the direct route: Its matching lemma, premises, or required equality connection are unavailable
- Boundary: Cards 003/043 also describe conditional constructor fallbacks; failure of a direct bridge does not exclude those original fallback cases

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

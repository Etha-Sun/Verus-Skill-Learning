# Direct reuse of an existing lemma or trait bridge

## Scope

- Consult when: A library lemma matches an algebraic goal, or the goal connects serialization, view equality, and marshalability
- Consult when: The selected direct route has a matching installed/declared lemma or trait contract with available premises
- Not for the direct route: Its matching lemma, premises, or required equality connection are unavailable
- Boundary: Cards 003/043 also describe conditional constructor fallbacks; failure of a direct bridge does not exclude those original fallback cases

<a id="original-card-003"></a>
## Original card-003

Source cards: card-003

**Trigger:** A proof obligation asks to show that two structured values have equal views under assumptions that both values are marshalable and their serialized representations are equal; an existing trait or generated instance already promises view equality under those assumptions.
**Action:** Invoke the existing proof method whose contract maps marshalability and equal serialization to view equality. If needed, expose the view-equal relation and assert the required structural view equality so the open view-specification definitions can unfold. If the solver still cannot close the structural equality, case-split on the constructors and propagate field equalities.
**Why:** The trait-level proof is already trusted background and corresponds exactly to the function premises. The generated view equality and view definitions are open, so once the relation is exposed, structural view equality can be derived by definitional unfolding without inventing a new assumption.
**Validate:** Run the verifier and confirm zero errors; run the proof-safety comparison and confirm it passes. Ensure only the proof body changed and no specifications or executable behavior were modified.
**Avoid when:** The trait method or generated instance is unavailable in the current source, or the view-equal relation does not logically imply the structural view equality for the particular type. Do not weaken the specification or add a trusted body if the relation is insufficient.

- Distinguish from [set-equality-membership-witness](set-equality-membership-witness.md): Use this route only when the existing lemma itself closes the algebraic goal; otherwise set equality requires membership extensionality and explicit witnesses.

- Distinguish from [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque-spec route needs an open counterpart/connector or fixed-width lemma, not a direct goal-matching lemma.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Use this route only when the existing lemma itself closes the algebraic goal; otherwise set equality requires membership extensionality and explicit witnesses.

- Related [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque-spec route needs an open counterpart/connector or fixed-width lemma, not a direct goal-matching lemma.

- Related [view-equality-constructor-case](view-equality-constructor-case.md): Direct bridge first tries packaged declaration/trait route; this family is the fallback explicit case analysis.

- Related [library-broadcast-activation](library-broadcast-activation.md): Direct bridge invokes a matching lemma; broadcast route explicitly brings a trusted axiom group into proof scope for case analysis.

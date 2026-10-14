# Direct reuse of an existing lemma or trait bridge

## Scope

- Consult when: A library lemma matches an algebraic goal, or the goal connects serialization, view equality, and marshalability
- Consult when: The selected direct route has a matching installed/declared lemma or trait contract with available premises
- Not for the direct route: Its matching lemma, premises, or required equality connection are unavailable
- Boundary: Cards 003/043 also describe conditional constructor fallbacks; failure of a direct bridge does not exclude those original fallback cases

<a id="installed-library-lemma-direct"></a>
## Direct reuse of an installed library lemma matching the proof obligation

Source cards: card-001

**Trigger:** A proof obligation is a known algebraic property about library types, such as mapping over a union of sets, and an installed library already provides a lemma whose conclusion matches that obligation.
**Action:** Before constructing a manual case analysis, inspect the installed library definitions for a lemma with the same conclusion. If one exists, invoke that lemma in the proof body with arguments matching the current obligation and let the verifier close the postcondition.
**Why:** Existing verified library lemmas have already handled witness extraction and extensional reasoning. Reusing such a lemma is narrower and faster than re-proving the same property. In the observed set-image union task, every continuation that selected the direct library lemma verified on the first attempt.
**Validate:** Run the verifier and confirm zero errors; run the proof-safety comparison and confirm it passes. Check that only the proof body changed and no signatures or specifications were modified.
**Avoid when:** The installed library has no lemma matching the goal, the lemma requires additional premises not currently available, or the lemma uses an equality form that the verifier cannot connect to the present postcondition.

- Distinguish from [set-equality-membership-witness](set-equality-membership-witness.md): Use this route only when the existing lemma itself closes the algebraic goal; otherwise set equality requires membership extensionality and explicit witnesses.

- Distinguish from [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque-spec route needs an open counterpart/connector or fixed-width lemma, not a direct goal-matching lemma.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Use this route only when the existing lemma itself closes the algebraic goal; otherwise set equality requires membership extensionality and explicit witnesses.

- Related [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque-spec route needs an open counterpart/connector or fixed-width lemma, not a direct goal-matching lemma.

- Related [view-equality-constructor-case](view-equality-constructor-case.md): Direct bridge first tries packaged declaration/trait route; this family is the fallback explicit case analysis.

- Related [library-broadcast-activation](library-broadcast-activation.md): Direct bridge invokes a matching lemma; broadcast route explicitly brings a trusted axiom group into proof scope for case analysis.

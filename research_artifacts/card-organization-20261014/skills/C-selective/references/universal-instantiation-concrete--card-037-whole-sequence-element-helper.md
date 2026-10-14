# Instantiate an available universal fact at a concrete term

## Scope

- Consult when: A whole-sequence, entailment/validity, or temporal universal fact is available but not used at a concrete index, execution, or term
- Consult when: No trigger-inference diagnostic is present, or local aliases hide the matching form
- Not for: A trigger-inference error requires explicit trigger annotation
- Not for: The failure is a missing antecedent inside a quantified proof block

<a id="card-037-whole-sequence-element-helper"></a>
## Whole-sequence property at loop index via in-bounds element helper

Source cards: card-037

**Trigger:** A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically.
**Action:** Introduce a small proof-only helper that takes the whole-sequence property and an in-bounds index and concludes the element property, then call that helper in the loop body. Use the concrete indexed term at the call site so the quantifier trigger can match.
**Why:** A bounded forall often requires an explicit instantiation step; a lemma localizes that step and keeps the loop body legible.
**Validate:** Rerun Verus; the previously failing element assertion or call precondition should become provable.
**Avoid when:** The element property is not actually derivable from the whole-sequence assumption under the available bounds, or the index is not guaranteed to be in range.

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route changes quantifier annotations; this route asserts or applies the universal fact at the needed concrete term.

- Distinguish from [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Antecedent/binder route fixes scope; this route fixes non-instantiation of an already in-scope universal fact.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route changes quantifier annotations; this route asserts or applies the universal fact at the needed concrete term.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Antecedent/binder route fixes scope; this route fixes non-instantiation of an already in-scope universal fact.

- Related [loop-termination-and-invariants](loop-termination-and-invariants.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

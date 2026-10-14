# Instantiate an available universal fact at a concrete term

## Scope

- Consult when: A whole-sequence, entailment/validity, or temporal universal fact is available but not used at a concrete index, execution, or term
- Consult when: No trigger-inference diagnostic is present, or local aliases hide the matching form
- Not for: A trigger-inference error requires explicit trigger annotation
- Not for: The failure is a missing antecedent inside a quantified proof block

<a id="card-076-alias-inline-trigger-instantiation"></a>
## Recursive helper stability via alias inlining and trigger assertions

Source cards: card-076

**Trigger:** A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases.
**Action:** Inline the local aliases back into the expanded suffix and predicate expressions used by the helper's preconditions. Then explicitly assert each quantified hypothesis the helper requires, using a conditional branch on the antecedent and asserting the exact quantified trigger term to force instantiation of the always fact.
**Why:** Local aliases can change the syntactic form that Verus uses to match quantifier triggers, so the propagated fact is not instantiated at the call site. Inlining restores the exact forms, and an explicit assertion of the trigger term invokes the universal fact.
**Validate:** Rerun Verus; the helper's quantified precondition should now be discharged and the surrounding proof should close. Confirm Lynette passes.
**Avoid when:** The aliases are not implicated in trigger matching or the necessary facts are not available as trusted quantified facts. Changing trigger selection is not required; accepting an existing automatic trigger to suppress a note is different from forcing instantiation.

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route changes quantifier annotations; this route asserts or applies the universal fact at the needed concrete term.

- Distinguish from [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Antecedent/binder route fixes scope; this route fixes non-instantiation of an already in-scope universal fact.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route changes quantifier annotations; this route asserts or applies the universal fact at the needed concrete term.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Antecedent/binder route fixes scope; this route fixes non-instantiation of an already in-scope universal fact.

- Related [loop-termination-and-invariants](loop-termination-and-invariants.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

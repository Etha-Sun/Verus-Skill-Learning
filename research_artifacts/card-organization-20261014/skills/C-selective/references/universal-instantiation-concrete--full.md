# Instantiate an available universal fact at a concrete term

## Scope

- Consult when: A whole-sequence, entailment/validity, or temporal universal fact is available but not used at a concrete index, execution, or term
- Consult when: No trigger-inference diagnostic is present, or local aliases hide the matching form
- Not for: A trigger-inference error requires explicit trigger annotation
- Not for: The failure is a missing antecedent inside a quantified proof block

## Rules

- [Whole-sequence property at loop index via in-bounds element helper](#card-037-whole-sequence-element-helper)
- [Entailment/validity premise instantiated as full implication at execution](#card-058-entailment-implication-concrete)
- [Recursive helper stability via alias inlining and trigger assertions](#card-076-alias-inline-trigger-instantiation)

<a id="card-037-whole-sequence-element-helper"></a>
## Whole-sequence property at loop index via in-bounds element helper

Source cards: card-037

**Trigger:** A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically.
**Action:** Introduce a small proof-only helper that takes the whole-sequence property and an in-bounds index and concludes the element property, then call that helper in the loop body. Use the concrete indexed term at the call site so the quantifier trigger can match.
**Why:** A bounded forall often requires an explicit instantiation step; a lemma localizes that step and keeps the loop body legible.
**Validate:** Rerun Verus; the previously failing element assertion or call precondition should become provable.
**Avoid when:** The element property is not actually derivable from the whole-sequence assumption under the available bounds, or the index is not guaranteed to be in range.

<a id="card-058-entailment-implication-concrete"></a>
## Entailment/validity premise instantiated as full implication at execution

Source cards: card-058

**Trigger:** A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed. **Action:** Before using the premise at a concrete execution, assert the full implication-form satisfaction for that execution, not just the conclusion. Then apply the implication with the antecedent and conclude the right-hand side. This uses the existing universal hypothesis rather than adding any new trusted fact. **Why:** An entailment expands to a universal quantifier over executions, and SMT instantiation often needs the surface form of the implication applied to the chosen execution. **Validate:** Re-run Verus; the previously failing assertion should be discharged and the final target should close. **Avoid when:** The premise is not an entailment or validity over the same execution type, or the selected implication term does not match the premise's syntactic form; use a helper lemma or a different unfolding in that case.

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

# Instantiate an available universal fact at a concrete term

## Scope

- Consult when: A whole-sequence, entailment/validity, or temporal universal fact is available but not used at a concrete index, execution, or term
- Consult when: No trigger-inference diagnostic is present, or local aliases hide the matching form
- Not for: A trigger-inference error requires explicit trigger annotation
- Not for: The failure is a missing antecedent inside a quantified proof block

<a id="card-058-entailment-implication-concrete"></a>
## Entailment/validity premise instantiated as full implication at execution

Source cards: card-058

**Trigger:** A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed. **Action:** Before using the premise at a concrete execution, assert the full implication-form satisfaction for that execution, not just the conclusion. Then apply the implication with the antecedent and conclude the right-hand side. This uses the existing universal hypothesis rather than adding any new trusted fact. **Why:** An entailment expands to a universal quantifier over executions, and SMT instantiation often needs the surface form of the implication applied to the chosen execution. **Validate:** Re-run Verus; the previously failing assertion should be discharged and the final target should close. **Avoid when:** The premise is not an entailment or validity over the same execution type, or the selected implication term does not match the premise's syntactic form; use a helper lemma or a different unfolding in that case.

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route changes quantifier annotations; this route asserts or applies the universal fact at the needed concrete term.

- Distinguish from [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Antecedent/binder route fixes scope; this route fixes non-instantiation of an already in-scope universal fact.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route changes quantifier annotations; this route asserts or applies the universal fact at the needed concrete term.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Antecedent/binder route fixes scope; this route fixes non-instantiation of an already in-scope universal fact.

- Related [loop-termination-and-invariants](loop-termination-and-invariants.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

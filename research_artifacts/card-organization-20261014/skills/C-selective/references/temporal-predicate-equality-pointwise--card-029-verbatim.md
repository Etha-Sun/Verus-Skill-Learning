# Temporal or spec-level object equality via mutual entailment and pointwise index reasoning

## Scope

- Consult when: Goal is equality of temporal/spec-level function or operator objects such as universal/always/nested applications
- Consult when: Direct object equality is not automatic
- Consult when: Pointwise index/suffix arithmetic and existing equality lemmas can discharge entailments
- Not for: Built-in extensional equality already suffices
- Not for: Equality is between non-temporal logical predicates

<a id="card-029-verbatim"></a>
## Temporal equality with universal and always operators; existing commutation helpers and reflexive entailment premises

Source cards: card-029

**Trigger:** A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier. **Action:** Instantiate the helper that moves always across the universal using two pointwise predicate families that differ only in whether the always wraps the implication. For each index, discharge the helper precondition by reducing both entailment directions to self-entailment of the same always predicate; a local reflexivity assertion is sufficient. Then instantiate the helper that commutes a plain implication through the universal quantifier. Chain the resulting equalities under congruence of always to close the target. **Why:** The two helper postconditions rewrite the left side into the right side in two compatible steps. The precondition is definitional reflexivity after the always operation is applied to the same underlying predicate, so it does not require a new lemma. **Validate:** Rerun Verus and expect verification with zero proof errors; then run the behavior-preservation checker and confirm it exits successfully. In the observed traces this helper chain closed the postcondition, while a missing local proof block produced a syntax error and was fixed by adding a local reflexivity assertion. **Avoid when:** Do not attempt to unfold all temporal definitions globally or introduce a new universal temporal rule. Do not skip the precondition assertion for the always-moving helper, because its external body still requires that premise to be discharged.

- Distinguish from [predicate-equality-mutual-entailment](predicate-equality-mutual-entailment.md): Predicate-equality route handles logical predicate conjunction equality; temporal route handles function/temporal objects with index arithmetic.

- Distinguish from [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): Existential-witness route chooses message-like witnesses; temporal object equality route uses pointwise entailment and index identities.

- Related [predicate-equality-mutual-entailment](predicate-equality-mutual-entailment.md): Predicate-equality route handles logical predicate conjunction equality; temporal route handles function/temporal objects with index arithmetic.

- Related [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): Existential-witness route chooses message-like witnesses; temporal object equality route uses pointwise entailment and index identities.

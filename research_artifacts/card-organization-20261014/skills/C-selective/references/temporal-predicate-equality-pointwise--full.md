# Temporal or spec-level object equality via mutual entailment and pointwise index reasoning

## Scope

- Consult when: Goal is equality of temporal/spec-level function or operator objects such as universal/always/nested applications
- Consult when: Direct object equality is not automatic
- Consult when: Pointwise index/suffix arithmetic and existing equality lemmas can discharge entailments
- Not for: Built-in extensional equality already suffices
- Not for: Equality is between non-temporal logical predicates

## Rules

- [Temporal equality with universal and always operators; existing commutation helpers and reflexive entailment premises](#card-029-verbatim)
- [Single-versus-nested temporal operator equality; mutual entailment and pointwise suffix-index identities](#card-070-verbatim)

<a id="card-029-verbatim"></a>
## Temporal equality with universal and always operators; existing commutation helpers and reflexive entailment premises

Source cards: card-029

**Trigger:** A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier. **Action:** Instantiate the helper that moves always across the universal using two pointwise predicate families that differ only in whether the always wraps the implication. For each index, discharge the helper precondition by reducing both entailment directions to self-entailment of the same always predicate; a local reflexivity assertion is sufficient. Then instantiate the helper that commutes a plain implication through the universal quantifier. Chain the resulting equalities under congruence of always to close the target. **Why:** The two helper postconditions rewrite the left side into the right side in two compatible steps. The precondition is definitional reflexivity after the always operation is applied to the same underlying predicate, so it does not require a new lemma. **Validate:** Rerun Verus and expect verification with zero proof errors; then run the behavior-preservation checker and confirm it exits successfully. In the observed traces this helper chain closed the postcondition, while a missing local proof block produced a syntax error and was fixed by adding a local reflexivity assertion. **Avoid when:** Do not attempt to unfold all temporal definitions globally or introduce a new universal temporal rule. Do not skip the precondition assertion for the always-moving helper, because its external body still requires that premise to be discharged.

<a id="card-070-verbatim"></a>
## Single-versus-nested temporal operator equality; mutual entailment and pointwise suffix-index identities

Source cards: card-070

**Trigger:** A postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails.
**Action:** Prove the two semantic entailment directions separately. In the direction from the nested application to the single application, instantiate the outer and inner quantified statements at a concrete index and at zero. In the direction from the single application to the nested application, instantiate at the sum of two arbitrary indices. For each direction, prove equality of the underlying state or suffix objects pointwise at every index using simple arithmetic identities and the supplied pointwise-equality lemma, then invoke the supplied equality lemma for the spec-level objects.
**Why:** Equality of function-like specification objects is not derived automatically. The prover needs pointwise equality plus the supplied lemma that turns pointwise equality into object equality. The remaining mathematical work is arithmetic over indices and the existing object equality lemmas.
**Validate:** Run Verus after each entailment direction and ensure both verify before invoking the final equality lemma. Then run the proof-only safety comparison. Do not add new trusted bodies or weaken contracts; existing trusted declarations are background only.
**Avoid when:** Built-in extensional equality for those objects already suffices without manual pointwise evidence, or the arithmetic identity needed for the index shift is not available in scope.

- Distinguish from [predicate-equality-mutual-entailment](predicate-equality-mutual-entailment.md): Predicate-equality route handles logical predicate conjunction equality; temporal route handles function/temporal objects with index arithmetic.

- Distinguish from [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): Existential-witness route chooses message-like witnesses; temporal object equality route uses pointwise entailment and index identities.

- Related [predicate-equality-mutual-entailment](predicate-equality-mutual-entailment.md): Predicate-equality route handles logical predicate conjunction equality; temporal route handles function/temporal objects with index arithmetic.

- Related [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): Existential-witness route chooses message-like witnesses; temporal object equality route uses pointwise entailment and index identities.

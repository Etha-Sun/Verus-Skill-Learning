# Temporal or spec-level object equality via mutual entailment and pointwise index reasoning

## Scope

- Consult when: Goal is equality of temporal/spec-level function or operator objects such as universal/always/nested applications
- Consult when: Direct object equality is not automatic
- Consult when: Pointwise index/suffix arithmetic and existing equality lemmas can discharge entailments
- Not for: Built-in extensional equality already suffices
- Not for: Equality is between non-temporal logical predicates

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

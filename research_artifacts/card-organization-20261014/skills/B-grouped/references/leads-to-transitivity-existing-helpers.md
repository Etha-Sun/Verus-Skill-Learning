# Leads-to transitivity with existing temporal helpers

## Scope

- Consult when: Goal is a leads-to transitivity postcondition
- Consult when: Trusted entailment, always, eventually, implication, witness, execution equality, and backward propagation helpers exist
- Not for: Required helpers are absent or contracts changed
- Not for: Conclusion is not a leads-to transitivity

## Rules

- [Leads-to transitivity with existing temporal helpers](#rule-card-051-verbatim)

<a id="rule-card-051-verbatim"></a>
## Leads-to transitivity with existing temporal helpers

Source cards: card-051

**Trigger:** A leads-to transitivity proof has an empty body and only its postcondition fails, while the surrounding helper lemmas for entailment, always, eventually, implication application, witness selection, execution equality, and backward eventual propagation are already declared as trusted background.
**Action:** Fix an arbitrary execution satisfying the specification and apply the two entailment assumptions at that execution, then unfold the two always facts. For an arbitrary suffix where the first predicate holds, apply the implication to obtain eventually the intermediate predicate and select a witness time. Relate the doubly shifted suffix to the single suffix at the summed times, either by direct execution equality or by first asserting pointwise equality of the state functions; then apply the second implication at the summed suffix and propagate the eventually state backward to the current suffix. Reassemble this per-suffix implication into the always condition to close the transitivity postcondition.
**Why:** The two hypotheses are local implications at every suffix, but the conclusion requires crossing from the first predicate at one time through an intermediate predicate at another time. The supplied helper lemmas exactly provide introduction and elimination for the temporal quantifiers and witness, and the suffix index arithmetic is decidable by the verifier.
**Validate:** Run Verus and expect the single function to verify. Run Lynette and expect it to pass without executable changes. In the supplied traces, every branch reached one verified function and a passing comparison; variations only involved explicit pointwise equality versus leaving it to the solver, and different top-level implication forms.
**Avoid when:** The helper lemmas are not present or their contracts have changed, because this proof intentionally relies on those existing trusted declarations. Also avoid adding new axioms or using assumptions beyond the given helper lemmas.

- Distinguish from [final-liveness-helper-chain](final-liveness-helper-chain.md): Final-liveness route assembles invariant/stability/phase helpers; this route focuses on two-step temporal implication composition and suffix index alignment.

- Related [final-liveness-helper-chain](final-liveness-helper-chain.md): Transitivity route addresses one two-step entailment-composition step with suffix index alignment; final-liveness route assembles a multi-part invariant/stability/phase helper chain.

- Related [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise-lifting proves a single per-suffix entailment/leads-to relationship; this transitivity route composes two existing leads-to hypotheses through an intermediate witness time and shifted suffix arithmetic using existing temporal helpers.

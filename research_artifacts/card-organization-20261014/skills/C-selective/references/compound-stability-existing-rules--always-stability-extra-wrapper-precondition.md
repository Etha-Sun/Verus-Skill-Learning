# Compound temporal stability via existing stability and conjunction rules

## Scope

- Consult when: Target is a stable compound temporal predicate such as a conjunction of always-lifted predicates and/or finitely many universal fairness components
- Consult when: Existing stability, conjunction, or stabilization proof objects/macros are available
- Not for: Target is not a finite conjunction of always-lifted or similarly stable predicates
- Not for: Required local rules or proof objects are absent or incompatible

<a id="always-stability-extra-wrapper-precondition"></a>
## Repair extra always wrapper causing conjunction-stability precondition failure

Source cards: card-072

**Trigger:** An always-stability rule was given a temporal predicate already wrapped in always, and the following conjunction-stability call fails its precondition because the resulting stable form has an extra always wrapper.
**Action:** Pass the inner temporal predicate to the always-stability rule, removing the extra always wrapper but retaining the state-to-temporal lifting when the component began as a state predicate. Then combine stability of the intended always-wrapped conjuncts in the target's left-to-right association.
**Why:** The rule establishes stability of always applied to its temporal argument. Passing an already-always-wrapped argument proves a nested always form instead of stability of the intended conjunct. Raw state predicates still need lifting to the required temporal argument type.
**Validate:** After correcting the argument shape, the conjunction-stability preconditions are satisfied; Verus reports one verified and zero errors, and the safety comparison passes.
**Avoid when:** The rule does not take an inner temporal predicate or its contract intentionally expects another wrapper shape. Inspect the exact local contract; do not remove state-to-temporal lifting or claim a type-layer repair is sufficient when other conjunction premises are missing.

- Distinguish from [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise lifting route proves an entailment from states/suffixes; stability route combines existing stability rules in a structured predicate order.

- Related [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise lifting route proves an entailment from states/suffixes; stability route combines existing stability rules in a structured predicate order.

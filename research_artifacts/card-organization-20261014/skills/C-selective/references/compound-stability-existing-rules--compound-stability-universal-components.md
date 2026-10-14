# Compound temporal stability via existing stability and conjunction rules

## Scope

- Consult when: Target is a stable compound temporal predicate such as a conjunction of always-lifted predicates and/or finitely many universal fairness components
- Consult when: Existing stability, conjunction, or stabilization proof objects/macros are available
- Not for: Target is not a finite conjunction of always-lifted or similarly stable predicates
- Not for: Required local rules or proof objects are absent or incompatible

<a id="compound-stability-universal-components"></a>
## Compound temporal stability with universal fairness/action obligations

Source cards: card-026

**Trigger:** The goal is to prove that a compound temporal formula is stable, and that formula is a conjunction of an always-step property and several universally quantified fairness or action obligations. The direct goal fails or is too large to discharge at once.
**Action:** Establish stability separately for each conjunct. Prove stability of the always-step component by showing satisfaction at every suffix. For each universally quantified component, first prove the stability of an arbitrary instance and then lift stability through the universal quantifier. Recombine the stable conjuncts pairwise with a conjunction-stability lemma.
**Why:** Stability is preserved by conjunction. Separating the always and universal obligations lets per-action fairness lemmas and a suffix-shift lemma discharge each component, and pairwise recombination matches the structure of the original formula.
**Validate:** Run the verifier after each added helper. In the observed branched completions, this decomposition led to all functions verified with zero errors, and the completed candidate passed the proof-only safety comparison.
**Avoid when:** Avoid if any component lacks its necessary logical premise or if the conjunction-stability rule is itself only an unproven placeholder. Do not assume stability of an instance without proving it, and if recombination fails, identify which conjunct is missing before changing trigger annotations.

- Distinguish from [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise lifting route proves an entailment from states/suffixes; stability route combines existing stability rules in a structured predicate order.

- Related [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise lifting route proves an entailment from states/suffixes; stability route combines existing stability rules in a structured predicate order.

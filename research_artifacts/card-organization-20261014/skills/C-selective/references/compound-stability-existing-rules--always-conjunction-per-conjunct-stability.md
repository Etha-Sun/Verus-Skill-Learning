# Compound temporal stability via existing stability and conjunction rules

## Scope

- Consult when: Target is a stable compound temporal predicate such as a conjunction of always-lifted predicates and/or finitely many universal fairness components
- Consult when: Existing stability, conjunction, or stabilization proof objects/macros are available
- Not for: Target is not a finite conjunction of always-lifted or similarly stable predicates
- Not for: Required local rules or proof objects are absent or incompatible

<a id="always-conjunction-per-conjunct-stability"></a>
## Always-conjunction stability through per-conjunct always-stability rules

Source cards: card-045, card-071

**Trigger:**
- A proof function has an empty/incomplete body and its postcondition asks for stability/validity of a left-associative or left-nested conjunction of always-wrapped temporal predicates; card-045 specifically concerns large left-associative conjunctions where each always-wrapped predicate is already available in the same file, while card-071 addresses a stable form of a conjunction of always-lifted state predicates.

**Premises:**
- Existing always-stability rule for an always-wrapped temporal predicate and existing conjunction-stability rule/chaining helper are present in the file; card-045 emphasizes every conjunct is already available in the same file, and card-071 emphasizes existing combinator contracts.

**Action:**
- Inspect the target definition and record the exact left-to-right/left-nested order of the conjuncts before combining.
- Inspect the existing combinator contracts before establishing each conjunct stability.
- For each conjunct, prove stability using the existing always-stability rule, passing the inner temporal predicate of that conjunct (not an already-always-wrapped conjunct). If a component began as a state predicate, keep its state-to-temporal lifting.
- Combine the resulting stability facts in the same target order using the existing pairwise conjunction rule or its chaining helper, either by passing terms directly or binding local names.

**Why:**
- Stability is preserved by conjunction. Passing the inner predicate to the always-stability rule yields stability of each intended always-wrapped conjunct, and combining in definition order produces a syntactic match with the unfolded target instead of requiring a from-scratch temporal proof.

**Validate:**
- Run Verus and expect one verified function with zero errors; then run the proof-only safety comparison and confirm it passes. If the postcondition remains, re-check that every conjunct was included exactly once and in definition order; a lingering deprecation warning is not a proof error.

**Avoid when:**
- Do not use if the target is not a conjunction of predicates already wrapped in the always modality, or a conjunct is not shaped as the existing always-stability lemma accepts.
- Do not use if the required always-stability and conjunction-stability rules/helpers are absent from the file or incompatible with the definitions.
- Do not use if the left-nested structure of the target does not match the available conjunction helper; in that case use the fresh diagnostic to guide a different proof step.


- Distinguish from [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise lifting route proves an entailment from states/suffixes; stability route combines existing stability rules in a structured predicate order.

- Related [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise lifting route proves an entailment from states/suffixes; stability route combines existing stability rules in a structured predicate order.

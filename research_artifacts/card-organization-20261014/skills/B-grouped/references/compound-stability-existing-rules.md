# Compound temporal stability via existing stability and conjunction rules

## Scope

- Consult when: Target is a stable compound temporal predicate such as a conjunction of always-lifted predicates and/or finitely many universal fairness components
- Consult when: Existing stability, conjunction, or stabilization proof objects/macros are available
- Not for: Target is not a finite conjunction of always-lifted or similarly stable predicates
- Not for: Required local rules or proof objects are absent or incompatible

## Rules

- [Compound temporal stability with universal fairness/action obligations](#compound-stability-universal-components)
- [Always-conjunction stability through per-conjunct always-stability rules](#always-conjunction-per-conjunct-stability)
- [Reuse existing stabilization proof object/macro for lifted always-conjunction](#existing-stabilization-proof-object-lifted-conjunction)
- [Repair extra always wrapper causing conjunction-stability precondition failure](#always-stability-extra-wrapper-precondition)

<a id="compound-stability-universal-components"></a>
## Compound temporal stability with universal fairness/action obligations

Source cards: card-026

**Trigger:** The goal is to prove that a compound temporal formula is stable, and that formula is a conjunction of an always-step property and several universally quantified fairness or action obligations. The direct goal fails or is too large to discharge at once.
**Action:** Establish stability separately for each conjunct. Prove stability of the always-step component by showing satisfaction at every suffix. For each universally quantified component, first prove the stability of an arbitrary instance and then lift stability through the universal quantifier. Recombine the stable conjuncts pairwise with a conjunction-stability lemma.
**Why:** Stability is preserved by conjunction. Separating the always and universal obligations lets per-action fairness lemmas and a suffix-shift lemma discharge each component, and pairwise recombination matches the structure of the original formula.
**Validate:** Run the verifier after each added helper. In the observed branched completions, this decomposition led to all functions verified with zero errors, and the completed candidate passed the proof-only safety comparison.
**Avoid when:** Avoid if any component lacks its necessary logical premise or if the conjunction-stability rule is itself only an unproven placeholder. Do not assume stability of an instance without proving it, and if recombination fails, identify which conjunct is missing before changing trigger annotations.

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


<a id="existing-stabilization-proof-object-lifted-conjunction"></a>
## Reuse existing stabilization proof object/macro for lifted always-conjunction

Source cards: card-047, card-062

**Trigger:**
- The proof function has an empty/incomplete body and a postcondition that a finite conjunction of always-lifted state predicates is stable under temporal rules; existing stability and conjunction proof objects or a helper macro are already present in the file.

**Premises:**
- Each component predicate can be lifted from state to temporal form, and the local stability/conjunction proof object or helper macro accepts those lifted arguments.

**Action:**
- Inspect the local temporal rule definitions and reuse the existing stability and conjunction-combination machinery, or the helper macro already present in the file, rather than unfolding temporal definitions by hand.
- Use the existing temporal stabilization proof object to combine the same component predicates that appear in the invariant; wrap each raw state predicate in the operation that lifts a state predicate to a temporal predicate.
- Present the arguments as a plain comma-separated list without a separator after the final argument; leave all other declarations and specifications unchanged.
- Apply/reuse the selected machinery to each lifted state predicate in the same left-to-right order as the target predicate is constructed.

**Why:**
- The supplied rules or proof object express exactly the two facts needed: every always predicate is stable, and stable predicates are closed under conjunction. Passing lifted temporal arguments and matching target order lets Verus connect the proof steps to the target's left-associated structure; raw state predicates cause type errors and trailing separators may cause parser rejection.

**Validate:**
- Re-run Verus and confirm the postcondition or macro error becomes zero errors with only pre-existing warnings; then run the proof-only safety comparison and inspect that only the proof body changed.

**Avoid when:**
- Do not use when the target is not a finite conjunction of always-lifted state predicates, or the expected local stability and conjunction rules/proof object are absent or incompatible with the definitions.
- Do not pass raw state predicates when the proof object expects temporal predicates; keep the state-to-temporal lifting.
- Do not leave a trailing separator if the proof object's argument pattern rejects one.


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

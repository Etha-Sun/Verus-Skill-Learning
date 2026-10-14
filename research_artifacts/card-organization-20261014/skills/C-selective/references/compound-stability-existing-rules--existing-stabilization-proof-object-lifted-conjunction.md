# Compound temporal stability via existing stability and conjunction rules

## Scope

- Consult when: Target is a stable compound temporal predicate such as a conjunction of always-lifted predicates and/or finitely many universal fairness components
- Consult when: Existing stability, conjunction, or stabilization proof objects/macros are available
- Not for: Target is not a finite conjunction of always-lifted or similarly stable predicates
- Not for: Required local rules or proof objects are absent or incompatible

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


- Distinguish from [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise lifting route proves an entailment from states/suffixes; stability route combines existing stability rules in a structured predicate order.

- Related [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Pointwise lifting route proves an entailment from states/suffixes; stability route combines existing stability rules in a structured predicate order.

# Temporal entailment by pointwise/per-suffix lifting

## Scope

- Consult when: Goal is an entailment or leads-to relationship over cluster states or execution suffixes
- Consult when: Body is empty or only the final postcondition is unproved
- Consult when: Pointwise or per-suffix implication follows from open definitions
- Not for: Target is not an entailment/leads-to over states/suffixes
- Not for: Pointwise implication does not follow from available definitions

## Rules

- [Temporal entailment by pointwise/per-suffix lifting](#card-056-verbatim)

<a id="card-056-verbatim"></a>
## Temporal entailment by pointwise/per-suffix lifting

Source cards: card-056

**Trigger:** A proof function body is empty and Verus reports only the final entailment or leads-to postcondition unproved; the obligation is a universal relationship over cluster states or execution suffixes. **Action:** Prove the relationship in stages: first establish the pointwise implication over arbitrary states or the per-suffix implication using the implication form that assumes the antecedent; then lift that pointwise fact across every execution suffix or temporal wrapper; finally close the target by instantiating the given premise at an arbitrary execution and combining it with the lifted fact. **Why:** This decomposition supplies the small intermediate facts the solver needs instead of discharging a universally quantified conclusion all at once, and it follows the structure of the open state or temporal definitions. **Validate:** Re-run Verus after each stage; final success should report all proof functions verified with zero errors, aside from possible pre-existing deprecation or trigger notes, and the safety comparison should pass. **Avoid when:** The target is not an entailment or leads-to obligation over states and suffixes, or the needed pointwise implication does not follow from the available open definitions.

- Distinguish from [weak-fairness-pointwise-lemmas](weak-fairness-pointwise-lemmas.md): Weak-fairness route creates action precondition/outcome/preservation lemmas; this route lifts a single pointwise/per-suffix implication to a temporal goal.

- Distinguish from [compound-stability-existing-rules](compound-stability-existing-rules.md): Stability route combines existing stability/conjunction rules; this route proves the entailment itself by pointwise lifting.

- Related [weak-fairness-pointwise-lemmas](weak-fairness-pointwise-lemmas.md): Weak-fairness route creates action precondition/outcome/preservation lemmas; this route lifts a single pointwise/per-suffix implication to a temporal goal.

- Related [compound-stability-existing-rules](compound-stability-existing-rules.md): Stability route combines existing stability/conjunction rules; this route proves the entailment itself by pointwise lifting.

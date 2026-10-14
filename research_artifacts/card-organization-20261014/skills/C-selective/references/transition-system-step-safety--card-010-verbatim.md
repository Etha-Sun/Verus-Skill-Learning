# State-machine invariant and step-safety lemmas

## Scope

- Consult when: Goal is an invariant, preservation, or safety property over a finite state-machine transition relation
- Consult when: Step cases can be pattern-matched or decomposed into finite local analyses
- Not for: Transition relation is uninterpreted or unbounded
- Not for: Preservation is genuinely false without an additional missing invariant

<a id="card-010-verbatim"></a>
## card-010

Source cards: card-010

**Trigger:** Verus reports an unsatisfied temporal postcondition requiring a specification to entail that a state predicate holds at every point in the future, while the relevant proof function body is empty.

**Action:** Use the supplied temporal induction rule for state invariants. Establish both premises: every initial state satisfying the system initialization also satisfies the state predicate, and whenever a state satisfying the predicate takes a next transition, the successor state also satisfies it. Prove the preservation premise by matching on every top-level step variant and reusing the corresponding transition identities.

**Why:** The state-invariant induction rule's conclusion exactly matches the temporal target. Because the system specification includes initial-state and next-transition entailments, discharging those two premises closes the goal without manually reasoning about arbitrary execution indices.

**Validate:** Run the Verus checker and expect zero errors with all proof functions verified, then run the proof-safety comparison tool and require exit zero.

**Avoid when:** The environment does not provide such an induction rule, the transition relation is not defined as a finite step match, or preservation is genuinely false because some step can introduce a bad state without an additional missing invariant.

- Distinguish from [nondeterministic-step-result](nondeterministic-step-result.md): Nondeterministic-step route is about not reconstructing a result through one nonunique witness, rather than proving preservation lemmas.

- Related [nondeterministic-step-result](nondeterministic-step-result.md): Nondeterministic-step route is about not reconstructing a result through one nonunique witness, rather than proving preservation lemmas.

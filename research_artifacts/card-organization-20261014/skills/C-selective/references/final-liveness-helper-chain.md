# Final liveness theorem assembled from existing helper chain

## Scope

- Consult when: Final liveness theorem needs invariant derivation, stability, base liveness, phase descent, and condition unpacking
- Consult when: The corresponding helper lemmas already exist and their preconditions match the current proof state
- Not for: Required helper prerequisites are missing
- Not for: Approach would require weakening specs or adding trusted bodies

## Rules

- [Final liveness theorem assembled from existing helper chain](#final-liveness-helper-chain-card-031)

<a id="final-liveness-helper-chain-card-031"></a>
## Final liveness theorem assembled from existing helper chain

Source cards: card-031

**Trigger:** A final liveness theorem has an empty or partial body and its postcondition is a desired-state leads-to current-state property, while invariant derivation lemmas, stability lemmas, a base liveness lemma, phase-descent lemmas, and a condition unpacking helper already exist. **Action:** First derive from the input specification that it entails the step-fairness predicate, then obtain the derived invariant bundle and combine them to entail the stable specification conjunction with invariants. Establish the stability facts with their existing lemmas. Transfer the non-interference condition to the stable specification and instantiate the base liveness lemma. Bridge the recursive phase accumulation to the all-phase bundle, descend through the phase lemmas, and use the condition-unpacking helper to move the desired-state assumption from the environment into the antecedent of the leads-to formula. Close by transitivity with any required associativity or trivial-conjunct rewrites. **Why:** Each step corresponds to an existing helper whose precondition matches the current proof state, so the proof composes those helpers rather than inventing new reasoning. The final unpack changes the shape of the already-established implication into the desired leads-to statement. **Validate:** Rerun Verus and confirm zero proof errors, then run the behavior-preservation comparison. In the observed successes this full chain verified; intermediate syntactic mismatches for associativity or trivial conjuncts were resolved by adding small equality or transitivity assertions. **Avoid when:** Do not attempt to prove the final implication directly before deriving the invariants and stability facts, since the base liveness lemma cannot be instantiated without them. Do not omit the associativity or trivial-predicate equality rewrites when the unpack helper precondition does not match syntactically. Never weaken specifications or add trusted bodies.

- Distinguish from [leads-to-transitivity-existing-helpers](leads-to-transitivity-existing-helpers.md): Transitivity route addresses one entailment-composition step; final-liveness route composes a multi-part liveness chain.

- Related [leads-to-transitivity-existing-helpers](leads-to-transitivity-existing-helpers.md): Transitivity route addresses one entailment-composition step; final-liveness route composes a multi-part liveness chain.

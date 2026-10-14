# Recursive phase accumulation to all-phase bundle bridge

## Scope

- Consult when: Phase-descent lemma precondition uses recursive next-phase predicate while base liveness concludes all-phase bundle
- Consult when: Verus rejects descent until equivalence between recursive accumulation and bundle is exposed
- Not for: No recursive phase accumulation/all-phase mismatch exists
- Not for: Unsupported reveal and explicit equality chain both unavailable

## Rules

- [Recursive phase accumulation to all-phase bundle bridge](#phase-accumulation-bridge)

<a id="phase-accumulation-bridge"></a>
## Recursive phase accumulation to all-phase bundle bridge

Source cards: card-030

**Trigger:** A liveness proof reaches a phase-descent lemma whose premise uses the next phase index, while the base liveness lemma concludes the all-phase assumption bundle. Verus rejects the first descent with a precondition about the next phase predicate unless an equality between the recursive phase accumulation and the all-phase bundle is established. **Action:** Before invoking the phase-descent lemma for the highest index, expose enough of the recursive phase accumulation so the verifier sees that it has the same conjunctive structure as the all-phase assumption bundle. This can be done by a fuel-based reveal of the recursive definition followed by an equality between the two temporal predicates, or by a chain of pointwise equivalence assertions from the top index down to the base. Then use the existing temporal predicate equality lemma or direct equality to substitute one side for the other, and proceed with the downward phase descent. **Why:** The base liveness lemma is stated with the all-phase assumption bundle, while the first phase-descent step requires the recursive predicate at one higher index. The solver does not automatically unfold recursive predicates far enough to connect these forms, so the missing bridge blocks the descent. Exposing the recursive definition makes the two sides visibly equal without adding a new trusted rule. **Validate:** Rerun Verus and check whether the prior precondition failure moves to a later stage or disappears. In the successful traces, after adding a fuel reveal or stepwise equalities the proof reached zero errors and the behavior-preservation checker passed. **Avoid when:** Do not assume the equality holds without exposing the recursive definition, and do not add a new temporal lemma. If an unsupported unfolding form is rejected, switch to the available fuel-reveal or explicit equality-chain style rather than repeating the same unsupported edit.

- Distinguish from [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque-spec route uses library open counterparts or fixed-width lemmas; phase bridge exposes a recursive temporal predicate by fuel reveal or stepwise equalities.

- Related [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque-spec route uses library open counterparts or fixed-width lemmas; phase bridge exposes a recursive temporal predicate by fuel reveal or stepwise equalities.

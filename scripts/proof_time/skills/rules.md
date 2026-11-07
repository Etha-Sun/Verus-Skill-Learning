## Writing proofs that are cheap for the solver

1. Every assert(P) is an extra proof obligation. If P is a large predicate (a wf()/invariant/inv_* predicate, next_step(...), a refinement relation, or equality of whole structs/records) and the final goal does not need P as a stepping stone, the solver must unfold P's definition and case-split just to prove it. Such asserts are the most common source of avoidable cost.
2. An `assert forall ... by { }` with an empty or trivial body that restates a property not used afterwards forces quantifier reasoning for nothing.
3. Asserts of small facts (simple equalities, arithmetic, a single membership) are usually cheap whether needed or not.
4. Statements that bridge to a lemma call (they establish the lemma's precondition) are usually needed; deleting them breaks the proof.

Learned from measured single-statement deletions in earlier proofs:
1. Remove assertions whose conclusion is not used later; if unsure, comment why it is needed.
2. Do not assert facts SMT can already derive (simple arithmetic, equalities, lengths) unless they trigger a required quantifier; redundant assertions can cause trigger explosions.
3. Factor generic expensive subproofs (sequence equality, map/conguence, fold bounds) into top-level lemmas instead of inline `assert ... by { ... }`.
4. Prove only the specific witness or instance required; avoid full implications, `choose`/case splits, or exhaustive subproofs when a single direction or witness suffices.
5. Keep assertions that introduce a witness, instantiate a quantifier for a specific term, or connect temporal/state/next-step facts to the current goal.

Costly-deletable statements usually restate known facts, prove unused generalizations, or duplicate existing library results. Needed statements supply new instances, witnesses, or bridge definitions to the obligation being proved.

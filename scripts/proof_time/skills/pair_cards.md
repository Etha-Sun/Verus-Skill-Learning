## Writing proofs that are cheap for the solver (learned from same-task proof pairs)

1. When a goal is an equality or union/map/fold fact over sequences or sets that would otherwise need pointwise membership or index reasoning, use an existing library or reusable helper lemma rather than writing a manual `choose`/quantified case split. Manual pointwise reasoning instantiates many quantifiers and arithmetic branches; library lemmas package the same fact with a better proof shape.

2. When several call sites need only small consequences of a large well-formedness invariant, create a small proof helper that reveals the invariant once and exposes narrow postconditions; avoid inlining the invariant open and extra assertions at each site. Repeatedly exposing the whole invariant gives the solver many irrelevant quantified facts.

3. When a proof must reestablish a large well-formedness predicate that is a conjunction of many component predicates, open its definition and then assert/prove the needed component predicates individually rather than asserting the whole conjunction as one goal. Smaller conjunct goals localize quantifier instantiation and produce reusable facts.

4. When proving that a field or property is preserved across a disjunctive transition relation, look for a stronger context fact that makes the conclusion weaker and easier, and match explicitly on the underlying transition/step constructors. Letting SMT unfold the disjunction and prove exact equality to an arbitrary old value is often much more expensive than constructor case analysis under a stronger precondition.

5. Before a destructive update or loop, extract old-state facts and bind ghost constants for values needed later. After the update, state only that specific objects or sequences are unchanged or chain update lemmas, rather than re-proving global facts in the post-state. This reduces old-state projections and global invariant reestablishment in each branch or iteration.

6. When a loop needs per-element properties of a collection, carry a direct quantified loop invariant with triggers over the collection rather than a recursively-defined aggregate validity predicate that must be unfolded per element. Direct per-element invariants give local solver goals and avoid unfolding the aggregate each iteration.

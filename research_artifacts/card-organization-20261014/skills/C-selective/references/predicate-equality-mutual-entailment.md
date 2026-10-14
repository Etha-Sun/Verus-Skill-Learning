# Logical predicate equality by mutual entailment

## Scope

- Consult when: Goal is equality between logical predicates, such as a predicate and its conjunction with an entailed predicate
- Consult when: Existing entailment-conjunction and mutual-entailment equality rules are available
- Not for: Equality is between temporal/function objects rather than logical predicates
- Not for: Required helpers are unavailable

## Rules

- [Logical predicate equality by mutual entailment](#predicate-equality-mutual-entailment-verbatim-card-020)

<a id="predicate-equality-mutual-entailment-verbatim-card-020"></a>
## Logical predicate equality by mutual entailment

Source cards: card-020

**Trigger:** A proof obligation is an equality between a logical predicate and the conjunction of that predicate with another predicate, under an assumption that the first predicate entails the second. The proof body is empty or only attempts the final equality directly.

**Action:** Use an existing rule that combines entailment to two predicates into entailment to their conjunction, supplying the first predicate for both the reflexive self-entailment and the given second entailment. If necessary, establish the reverse entailment from the conjunction back to the first predicate, which follows from the definition of conjunction. Then apply an existing rule that derives predicate equality from mutual entailment. Do not unfold definitions or add new assumptions.

**Why:** Equality between logical objects is often most easily proved by separately proving the two directions of the corresponding entailment relation. The existing helpers already encode the algebraic step, leaving only the reverse inclusion to discharge.

**Validate:** Verus reports one verified function and no errors after the helper calls, and the proof-only safety comparison passes.

**Avoid when:** The required helpers are unavailable, the equality is not between predicates with an entailment relation, or the reverse direction cannot be discharged from the definitions.

- Distinguish from [temporal-predicate-equality-pointwise](temporal-predicate-equality-pointwise.md): Temporal-object equality uses index/suffix pointwise reasoning; logical predicate equality uses entailment rules over boolean predicates.

- Related [temporal-predicate-equality-pointwise](temporal-predicate-equality-pointwise.md): Temporal-object equality uses index/suffix pointwise reasoning; logical predicate equality uses entailment rules over boolean predicates.

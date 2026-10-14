# Temporal or spec-level object equality via mutual entailment and pointwise index reasoning

## Scope

- Consult when: Goal is equality of temporal/spec-level function or operator objects such as universal/always/nested applications
- Consult when: Direct object equality is not automatic
- Consult when: Pointwise index/suffix arithmetic and existing equality lemmas can discharge entailments
- Not for: Built-in extensional equality already suffices
- Not for: Equality is between non-temporal logical predicates

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 029 concerns moving universal/always operators with matching commutation helpers; 070 concerns one versus two applications of the same operator and the associated index identities. Select by the actual two sides of the equality.

<a id="card-029-verbatim"></a>
- [card-029-verbatim](temporal-predicate-equality-pointwise--card-029-verbatim.md): Universal/always commutation equality.
  - When: Temporal equality has existing universal-commutation and always-moving helpers.
  - Avoid: Global unfolding, new trusted rules, or undischarged helper preconditions.

<a id="card-070-verbatim"></a>
- [card-070-verbatim](temporal-predicate-equality-pointwise--card-070-verbatim.md): Single versus nested temporal operator.
  - When: The failing postcondition equates one application of a temporal/spec operator with two applications.
  - Avoid: Built-in equality already suffices or the required index-shift identity is unavailable.

Read: `python3 reference_read.py temporal-predicate-equality-pointwise --rules ID [ID ...]`

Whole reference: `python3 reference_read.py temporal-predicate-equality-pointwise --full` or [temporal-predicate-equality-pointwise--full.md](temporal-predicate-equality-pointwise--full.md).

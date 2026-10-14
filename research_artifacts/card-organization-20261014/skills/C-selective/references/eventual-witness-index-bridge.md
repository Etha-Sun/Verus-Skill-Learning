# Eventual/existential temporal index witness bridging

## Scope

- Consult when: Goal is eventual or existential temporal obligation with an existing raw/action occurrence or witness
- Consult when: Lifted eventual/post-state assertion fails despite that witness
- Consult when: A concrete natural index or spec-level choice can expose the occurrence
- Not for: No occurrence or pointwise action-to-state implication exists
- Not for: Needed suffix/offset arithmetic cannot be established

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 008 starts with eventual action occurrence; 009 already has a raw state witness but lacks the suffix form. 061 covers obtaining a reachability index from an established existential and can overlap witness selection in 008. These are not mandatory successive reads.

<a id="card-008-verbatim"></a>
- [card-008-verbatim](eventual-witness-index-bridge--card-008-verbatim.md): Eventual action to post-state existence.
  - When: Eventual action occurrence is established but post-state existence still fails.
  - Avoid: Unusable occurrence triggers or missing pointwise action-to-post implication.

<a id="card-009-verbatim"></a>
- [card-009-verbatim](eventual-witness-index-bridge--card-009-verbatim.md): Absolute witness to suffix eventual state.
  - When: A raw state witness at an absolute shifted index does not establish eventual satisfaction on the current suffix.
  - Avoid: Unproved offset arithmetic or unavailable lifted-predicate unfolding.

<a id="card-061-verbatim"></a>
- [card-061-verbatim](eventual-witness-index-bridge--card-061-verbatim.md): Existential reachability witness.
  - When: A temporal branch has an existential reachability fact but a manual witness index is difficult.
  - Avoid: The existential is unproved or its witness property cannot support the next step.

Read: `python3 reference_read.py eventual-witness-index-bridge --rules ID [ID ...]`

Whole reference: `python3 reference_read.py eventual-witness-index-bridge --full` or [eventual-witness-index-bridge--full.md](eventual-witness-index-bridge--full.md).

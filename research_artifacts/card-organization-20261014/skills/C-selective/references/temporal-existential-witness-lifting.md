# Temporal existential witness lifting and leads-to composition

## Scope

- Consult when: Leads-to or equality temporal formula contains existential message/state predicates
- Consult when: Per-witness helper lemmas or witness-introduction/equality rules exist
- For leads-to: Check the selected rule's per-witness helper premises; card-016 also requires an atomic membership/equality witness source
- For equality (card-033): Check the trusted predicate-equality and witness-introduction rules and witness facts; a per-witness leads-to lemma is not its premise
- Not for: The selected rule's required trusted helpers or witness facts are unavailable

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 033 has an equality goal with equality/witness rules. 016 and 032 have leads-to goals and substantially overlapping witness lifting/composition: 016 emphasizes exact message templates, 032 intermediate predicates and final chaining. Neither leads-to entry is exclusive.

<a id="card-016-verbatim"></a>
- [card-016-verbatim](temporal-existential-witness-lifting--card-016-verbatim.md): Existential leads-to: message-template coverage.
  - When: Per-message leads-to lemmas exist but existential state predicates do not connect to their witness-specific templates.
  - Avoid: No trusted per-witness lemma or no atomic membership/equality witness source.

<a id="card-032-verbatim"></a>
- [card-032-verbatim](temporal-existential-witness-lifting--card-032-verbatim.md): Existential leads-to: intermediate-chain coverage.
  - When: Source/intermediate states are existential but supplied helper lemmas cover individual witnesses.
  - Avoid: A needed per-witness helper is absent/uninstantiable; separate legs may still leave the final chain open.

<a id="card-033-verbatim"></a>
- [card-033-verbatim](temporal-existential-witness-lifting--card-033-verbatim.md): Existential temporal equality, not just leads-to.
  - When: The goal is equality involving an existential temporal predicate and trusted equality/witness-introduction rules are supplied.
  - Avoid: Either required rule or witness facts are unavailable; an unassumed antecedent still needs its own check.

Read: `python3 reference_read.py temporal-existential-witness-lifting --rules ID [ID ...]`

Whole reference: `python3 reference_read.py temporal-existential-witness-lifting --full` or [temporal-existential-witness-lifting--full.md](temporal-existential-witness-lifting--full.md).

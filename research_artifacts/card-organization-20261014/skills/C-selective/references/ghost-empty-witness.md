# Concrete empty ghost aggregate or history witness

## Scope

- Consult when: Ghost aggregate or history field must be all-empty or contain empty sequences/set
- Consult when: Current ghost source is an arbitrary or unconstrained value
- Not for: Contract requires nonempty or partially populated value
- Not for: Field affects executable behavior

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** The aggregate entry addresses the returned multi-field ghost witness; the history entry addresses one initializer field constrained by an abstract initial-state relation. A history may be part of an aggregate, so both can match.

<a id="concrete-empty-ghost-aggregate"></a>
- [concrete-empty-ghost-aggregate](ghost-empty-witness--concrete-empty-ghost-aggregate.md): Empty ghost aggregate obligation.
  - When: An unconstrained ghost aggregate must have empty sequences and an empty derived set.
  - Avoid: The contract requires nonempty contents.

<a id="concrete-empty-ghost-history-initializer"></a>
- [concrete-empty-ghost-history-initializer](ghost-empty-witness--concrete-empty-ghost-history-initializer.md): Empty ghost history at initialization.
  - When: The abstract initial-state relation requires an empty history currently initialized arbitrarily.
  - Avoid: Nonempty history is required or the field affects executable behavior.

Read: `python3 reference_read.py ghost-empty-witness --rules ID [ID ...]`

Whole reference: `python3 reference_read.py ghost-empty-witness --full` or [ghost-empty-witness--full.md](ghost-empty-witness--full.md).

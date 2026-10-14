# Natural/integer and empty-sequence type annotations

## Scope

- Consult when: Verus type error arises from natural subtraction used as natural, natural length passed as integer index, or empty sequence needing element type
- Not for: Surrounding context already supplies enough type information
- Not for: Library interface accepts natural indices without conversion

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** Distinguish integer-valued predecessor subtraction where a natural is needed from a natural sequence length where an integer is needed. Empty-sequence element inference is a second case in the latter rule. The conversion directions are opposite, not interchangeable.

<a id="natural-predecessor-subtraction-conversion"></a>
- [natural-predecessor-subtraction-conversion](natural-integer-type-mismatch--natural-predecessor-subtraction-conversion.md): Natural predecessor expression: integer to natural mismatch.
  - When: A natural-induction helper expects a natural predecessor but subtraction produces an integer.
  - Avoid: The branch does not establish nonnegativity or safe conversion.

<a id="empty-sequence-length-annotation"></a>
- [empty-sequence-length-annotation](natural-integer-type-mismatch--empty-sequence-length-annotation.md): Sequence argument: unknown element type or natural to integer mismatch.
  - When: An empty sequence has unknown element type, or a natural sequence length is supplied to an integer-index interface.
  - Avoid: That type is already known or that interface accepts natural indices.

Read: `python3 reference_read.py natural-integer-type-mismatch --rules ID [ID ...]`

Whole reference: `python3 reference_read.py natural-integer-type-mismatch --full` or [natural-integer-type-mismatch--full.md](natural-integer-type-mismatch--full.md).

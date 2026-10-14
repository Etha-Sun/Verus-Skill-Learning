# Natural/integer and empty-sequence type annotations

## Scope

- Consult when: Verus type error arises from natural subtraction used as natural, natural length passed as integer index, or empty sequence needing element type
- Not for: Surrounding context already supplies enough type information
- Not for: Library interface accepts natural indices without conversion

<a id="empty-sequence-length-annotation"></a>
## Empty sequence element annotation and natural length casts

Source cards: card-066

**Trigger:** In a generic proof, an empty sequence argument triggers a type-inference error, or a sequence length is used where an integer index is expected and produces a natural-versus-integer mismatch. **Action:** Annotate the empty sequence with the element type parameter, and cast natural-number lengths to integer when passing them to subrange or split operations. Re-run Verus after making these narrow annotations. **Why:** Verus needs an explicit element type to resolve the empty sequence, and the sequence length is natural while many library operations take integer indices, so converting to integer resolves the type mismatch. **Validate:** Confirm the inference and mismatch diagnostics disappear, and the surrounding proof then verifies. **Avoid when:** The surrounding context already provides enough type information, or the library interface already accepts natural indices without a cast.

- Distinguish from [specialized-temporal-action-binder-type](specialized-temporal-action-binder-type.md): Specialized binder route fixes a partial-application residual payload type; this route handles natural/integer numeric and empty-sequence types.

- Related [specialized-temporal-action-binder-type](specialized-temporal-action-binder-type.md): Specialized binder route fixes a partial-application residual payload type; this route handles natural/integer numeric and empty-sequence types.

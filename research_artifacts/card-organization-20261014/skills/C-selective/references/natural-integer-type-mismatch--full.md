# Natural/integer and empty-sequence type annotations

## Scope

- Consult when: Verus type error arises from natural subtraction used as natural, natural length passed as integer index, or empty sequence needing element type
- Not for: Surrounding context already supplies enough type information
- Not for: Library interface accepts natural indices without conversion

## Rules

- [Natural predecessor subtraction conversion](#natural-predecessor-subtraction-conversion)
- [Empty sequence element annotation and natural length casts](#empty-sequence-length-annotation)

<a id="natural-predecessor-subtraction-conversion"></a>
## Natural predecessor subtraction conversion

Source cards: card-040

**Trigger:** While writing a recursive helper for natural-number induction, Verus reports a type mismatch when assigning the predecessor of a natural index, because subtraction produces an integer type rather than a natural.
**Action:** Convert the subtraction result back to a natural before assigning it, relying on the inductive branch condition that the current index is strictly positive so the predecessor is nonnegative.
**Why:** In the observed toolchain, subtraction between naturals is typed as an integer; the explicit conversion makes the type match while the branch condition ensures the conversion is sound.
**Validate:** Rerun Verus; the type mismatch should clear and verification should continue to any remaining proof obligation.
**Avoid when:** The branch condition does not guarantee the subtraction result is nonnegative, or the intended predecessor representation cannot safely be converted back to a natural at that point.

<a id="empty-sequence-length-annotation"></a>
## Empty sequence element annotation and natural length casts

Source cards: card-066

**Trigger:** In a generic proof, an empty sequence argument triggers a type-inference error, or a sequence length is used where an integer index is expected and produces a natural-versus-integer mismatch. **Action:** Annotate the empty sequence with the element type parameter, and cast natural-number lengths to integer when passing them to subrange or split operations. Re-run Verus after making these narrow annotations. **Why:** Verus needs an explicit element type to resolve the empty sequence, and the sequence length is natural while many library operations take integer indices, so converting to integer resolves the type mismatch. **Validate:** Confirm the inference and mismatch diagnostics disappear, and the surrounding proof then verifies. **Avoid when:** The surrounding context already provides enough type information, or the library interface already accepts natural indices without a cast.

- Distinguish from [specialized-temporal-action-binder-type](specialized-temporal-action-binder-type.md): Specialized binder route fixes a partial-application residual payload type; this route handles natural/integer numeric and empty-sequence types.

- Related [specialized-temporal-action-binder-type](specialized-temporal-action-binder-type.md): Specialized binder route fixes a partial-application residual payload type; this route handles natural/integer numeric and empty-sequence types.

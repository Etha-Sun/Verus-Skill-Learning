# Natural/integer and empty-sequence type annotations

## Scope

- Consult when: Verus type error arises from natural subtraction used as natural, natural length passed as integer index, or empty sequence needing element type
- Not for: Surrounding context already supplies enough type information
- Not for: Library interface accepts natural indices without conversion

<a id="natural-predecessor-subtraction-conversion"></a>
## Natural predecessor subtraction conversion

Source cards: card-040

**Trigger:** While writing a recursive helper for natural-number induction, Verus reports a type mismatch when assigning the predecessor of a natural index, because subtraction produces an integer type rather than a natural.
**Action:** Convert the subtraction result back to a natural before assigning it, relying on the inductive branch condition that the current index is strictly positive so the predecessor is nonnegative.
**Why:** In the observed toolchain, subtraction between naturals is typed as an integer; the explicit conversion makes the type match while the branch condition ensures the conversion is sound.
**Validate:** Rerun Verus; the type mismatch should clear and verification should continue to any remaining proof obligation.
**Avoid when:** The branch condition does not guarantee the subtraction result is nonnegative, or the intended predecessor representation cannot safely be converted back to a natural at that point.

- Distinguish from [specialized-temporal-action-binder-type](specialized-temporal-action-binder-type.md): Specialized binder route fixes a partial-application residual payload type; this route handles natural/integer numeric and empty-sequence types.

- Related [specialized-temporal-action-binder-type](specialized-temporal-action-binder-type.md): Specialized binder route fixes a partial-application residual payload type; this route handles natural/integer numeric and empty-sequence types.

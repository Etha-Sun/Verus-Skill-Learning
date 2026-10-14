# Concrete empty ghost aggregate or history witness

## Scope

- Consult when: Ghost aggregate or history field must be all-empty or contain empty sequences/set
- Consult when: Current ghost source is an arbitrary or unconstrained value
- Not for: Contract requires nonempty or partially populated value
- Not for: Field affects executable behavior

<a id="concrete-empty-ghost-history-initializer"></a>
## Concrete empty ghost history initializer

Source cards: card-073

**Trigger:** A concrete initializer's postcondition depends on an abstract initial-state relation that requires a ghost history field to be empty, while that ghost field is currently sourced from an unconstrained arbitrary value.
**Action:** Replace the arbitrary ghost initialization with a concrete empty sequence for that field, preserving executable behavior.
**Why:** A concrete empty value makes the required equality follow by construction, whereas an arbitrary value supplies no equality fact. Since the field is ghost-only, the change does not alter runtime behavior.
**Validate:** Run Verus and expect one verified and zero errors, leaving only any pre-existing deprecation warning. Then run the safety comparison and confirm it passes, and check that the final diff is limited to the intended ghost initializer line.
**Avoid when:** The abstract relation requires a non-empty or otherwise specific ghost history, or the field is not ghost-only and can affect executable behavior; in that case use the actual required initial value rather than unconditionally substituting an empty one.

- Distinguish from [existing-roundtrip-proof-mode](existing-roundtrip-proof-mode.md): Roundtrip route uses a trusted fact about a constructed return value; this route constructs a concrete empty ghost witness.

- Related [existing-roundtrip-proof-mode](existing-roundtrip-proof-mode.md): Roundtrip route uses a trusted fact about a constructed return value; this route constructs a concrete empty ghost witness.

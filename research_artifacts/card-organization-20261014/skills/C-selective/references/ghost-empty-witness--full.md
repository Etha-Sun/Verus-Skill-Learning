# Concrete empty ghost aggregate or history witness

## Scope

- Consult when: Ghost aggregate or history field must be all-empty or contain empty sequences/set
- Consult when: Current ghost source is an arbitrary or unconstrained value
- Not for: Contract requires nonempty or partially populated value
- Not for: Field affects executable behavior

## Rules

- [Concrete empty ghost aggregate](#concrete-empty-ghost-aggregate)
- [Concrete empty ghost history initializer](#concrete-empty-ghost-history-initializer)

<a id="concrete-empty-ghost-aggregate"></a>
## Concrete empty ghost aggregate

Source cards: card-054

**Trigger:** A function returning a ghost aggregate is required to prove that its contained sequences are all empty and that a sequence-derived set is empty, but its body returns an arbitrary or otherwise unconstrained witness.
**Action:** Construct a concrete aggregate value with every sequence field set to the empty sequence for the appropriate element type. Construct it in ghost context using a ghost local binding, and return that concrete witness.
**Why:** An arbitrary or unconstrained witness carries no facts that can discharge the equality postconditions. A concrete all-empty witness makes the field equalities definitional, and an empty sequence maps, filters, and converts to an empty set through the open specification functions.
**Validate:** Run Verus; if a spec-function mode error appears, ensure the construction and binding are ghost. After Verus passes, run Lynette; if it reports a deghosted token difference despite semantically identical code, preserve the original ghost binding name rather than introducing a new one.
**Avoid when:** The contract requires a nonempty or partially populated aggregate, or the derived property depends on non-empty contents; replacing the witness with empty values would then violate the specification.

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

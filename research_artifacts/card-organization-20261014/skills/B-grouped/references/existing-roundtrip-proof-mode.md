# Existing round-trip fact used in proof mode before value movement

## Scope

- Consult when: Deserializer/constructor success branch returns a value whose representation is not connected to the input
- Consult when: An existing trusted proof-mode round-trip lemma/axiom relates the reconstructed value and input
- Consult when: Its precondition is established before the input is moved
- Not for: No trusted round-trip proof-mode fact exists in current file
- Not for: Success branch does not establish the lemma premise

## Rules

- [Existing round-trip fact used in proof mode before value movement](#existing-roundtrip-proof-mode-046)

<a id="existing-roundtrip-proof-mode-046"></a>
## Existing round-trip fact used in proof mode before value movement

Source cards: card-046

**Trigger:** An executable deserializer or constructor returns a value in a success branch, but the postcondition still fails because the new value's specification-level representation is not connected to the input value, even though the file already has a trusted round-trip lemma or axiom relating a reconstructed value back to its input under a previously checked condition.
**Action:** Place a call to that existing round-trip lemma or axiom in proof mode, not in executable code, at the point where the precondition is already established and before the input value is moved into the constructor. Then let the verifier use the equality from that lemma to substitute the input representation for the constructed value. If the postcondition still has unsupported conjuncts, add targeted assertions only for those specific facts, such as representation equality, serialization length bound from the branch guard, and byte-range equality inherited from the surrounding deserializer, rather than changing specs or executable behavior.
**Why:** Proof-mode lemmas cannot be called directly from executable code; invoking them in proof context makes their conditional equality available to the verifier. Once the constructed value's representation is known to equal the input, the remaining marshalability, sortedness, size, and serialization equality obligations reduce to facts already available from the inner deserializer and the branch guards.
**Validate:** Run the verifier and expect one verified with zero errors. If a postcondition conjunct remains, use the diagnostic to identify which specific fact is not yet visible and add a corresponding assertion; avoid changing the returned value or the specification. Then run the proof-only safety comparison.
**Avoid when:** The needed round-trip property is not already declared as a trusted proof-mode lemma or axiom in the current file, because adding a new trusted axiom or assumption is not allowed. Also avoid this approach when the success branch does not actually establish the premise required by that existing lemma.

- Distinguish from [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque route obtains structural facts about closed/nondecreasing definitions; roundtrip route invokes an existing trusted roundtrip fact before moving the input.

- Related [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque route obtains structural facts about closed/nondecreasing definitions; roundtrip route invokes an existing trusted roundtrip fact before moving the input.

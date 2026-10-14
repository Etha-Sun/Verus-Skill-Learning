# Facts about opaque/nondecreasing spec functions via open or recursive counterparts

## Scope

- Consult when: Need a length, body, or equality fact about a closed/opaque/nondecreasing spec function or wrapper
- Consult when: Direct reveal or length assertion is rejected or fails
- Consult when: An open counterpart/connector, fixed-width lemma, or recursive proof helper can expose the body
- Not for: Direct revealing is supported or an existing direct lemma closes the goal
- Not for: Required open counterpart/connector/fixed-width lemma is unavailable

## Rules

- [Fuel reveal rejected for a nonrecursive spec wrapper](#rule-card-019)
- [Opaque fixed-width serialization length](#rule-card-021)
- [Length-prefixed serialization injectivity](#rule-card-053)

<a id="rule-card-019"></a>
## Fuel reveal rejected for a nonrecursive spec wrapper

Source cards: card-019

**Trigger:** An attempt to unfold a spec function with no decreasing clause using fuel-based revealing is rejected.

**Action:** Introduce a recursive proof helper that directly reasons about the underlying fold body, then in the original required proof call that helper and assert definitional equality between the required wrapper and the underlying fold expression used in the helper.

**Why:** Fuel-based revealing requires a decreasing clause that the wrapper lacks; asserting definitional equality with the open spec body is sufficient to transfer the helper's result to the required goal.

**Validate:** Rerun Verus after replacing the revealing call with the helper plus equality assertion; expect all functions verified. Then run the safety comparison and expect a zero exit.

**Avoid when:** The target spec function already supports direct revealing with a decreasing clause, or the body can be proven directly in the original function without a wrapper.

<a id="rule-card-021"></a>
## Opaque fixed-width serialization length

Source cards: card-021

**Trigger:** A direct assertion about the length of a closed serialization function fails, or attempting to reveal that function is rejected because it is closed. The fixed-width serialization length is needed for downstream bounds.

**Action:** Locate the allowed library's open version of the same conversion and the connector lemma relating the closed form to the open form. Build a reusable length fact by applying the connector, observing the open definition's finite structure, and transferring the resulting length back to the closed serialization. Use that reusable fact wherever the fixed-width serialization appears.

**Why:** The solver cannot see the body of a closed function, but it can unfold the open counterpart. The connector supplies the missing equality between the two forms, allowing the open structural fact to discharge the closed-function obligation.

**Validate:** The closed-function reveal rejection disappears, downstream fixed-width length assertions discharge, Verus reports no errors, and the proof-only safety comparison passes.

**Avoid when:** The library has no open counterpart or connector, or when the specification intentionally avoids reliance on low-level serialization details.

<a id="rule-card-053"></a>
## Length-prefixed serialization injectivity

Source cards: card-053

**Trigger:** A length-prefixed serialization injectivity proof needs a fixed-size header fact and sequence equality, but directly asserting the header length fails because a closed encoding spec function is opaque, and invoking a sequence-equality helper too early also fails.
**Action:** Locate an installed library lemma for the fixed-width little-endian or similar encoding that states both the encoded length and the decode round-trip. Invoke that lemma before asserting the header length. Split the serialized value into header and payload. Establish the header bytes equal pointwise using sequence concatenation index facts, and only then obtain sequence equality, either by an explicit per-index block supplied to the sequence-equality helper or by separate pointwise facts followed by the helper. Use a fully qualified helper path if the unqualified macro is not in scope.
**Why:** The closed encoding function is opaque to the verifier, so its length cannot be unfolded without an existing lemma. Sequence extensionality also requires equal lengths and equal elements, so the pointwise byte facts must be in context before the final equality step.
**Validate:** Rerun Verus after the edit; expect the header-length assertions to clear and the remaining proof obligations to progress. Run Lynette after Verus passes to confirm only ghost/proof code changed.
**Avoid when:** The serialized representation has no fixed-width header, or the installed standard library has no lemma for the fixed-width encoding and decoding round-trip; then the proof must rely on lower-level bit-vector reasoning and the observed short library-lemma route is not available.

- Distinguish from [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge uses an already goal-matching lemma/trait contract; opaque route must expose a definition through open counterpart/connector/helper.

- Distinguish from [existing-roundtrip-proof-mode](existing-roundtrip-proof-mode.md): Roundtrip route invokes an existing proof-mode roundtrip fact before a value is moved; opaque route obtains structural facts for closed/nondecreasing definitions.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge uses an already goal-matching lemma/trait contract; opaque route must expose a definition through open counterpart/connector/helper.

- Related [existing-roundtrip-proof-mode](existing-roundtrip-proof-mode.md): Roundtrip route invokes an existing proof-mode roundtrip fact before a value is moved; opaque route obtains structural facts for closed/nondecreasing definitions.

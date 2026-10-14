# Facts about opaque/nondecreasing spec functions via open or recursive counterparts

## Scope

- Consult when: Need a length, body, or equality fact about a closed/opaque/nondecreasing spec function or wrapper
- Consult when: Direct reveal or length assertion is rejected or fails
- Consult when: An open counterpart/connector, fixed-width lemma, or recursive proof helper can expose the body
- Not for: Direct revealing is supported or an existing direct lemma closes the goal
- Not for: Required open counterpart/connector/fixed-width lemma is unavailable

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

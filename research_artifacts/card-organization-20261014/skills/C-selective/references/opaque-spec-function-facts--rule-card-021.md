# Facts about opaque/nondecreasing spec functions via open or recursive counterparts

## Scope

- Consult when: Need a length, body, or equality fact about a closed/opaque/nondecreasing spec function or wrapper
- Consult when: Direct reveal or length assertion is rejected or fails
- Consult when: An open counterpart/connector, fixed-width lemma, or recursive proof helper can expose the body
- Not for: Direct revealing is supported or an existing direct lemma closes the goal
- Not for: Required open counterpart/connector/fixed-width lemma is unavailable

<a id="rule-card-021"></a>
## Opaque fixed-width serialization length

Source cards: card-021

**Trigger:** A direct assertion about the length of a closed serialization function fails, or attempting to reveal that function is rejected because it is closed. The fixed-width serialization length is needed for downstream bounds.

**Action:** Locate the allowed library's open version of the same conversion and the connector lemma relating the closed form to the open form. Build a reusable length fact by applying the connector, observing the open definition's finite structure, and transferring the resulting length back to the closed serialization. Use that reusable fact wherever the fixed-width serialization appears.

**Why:** The solver cannot see the body of a closed function, but it can unfold the open counterpart. The connector supplies the missing equality between the two forms, allowing the open structural fact to discharge the closed-function obligation.

**Validate:** The closed-function reveal rejection disappears, downstream fixed-width length assertions discharge, Verus reports no errors, and the proof-only safety comparison passes.

**Avoid when:** The library has no open counterpart or connector, or when the specification intentionally avoids reliance on low-level serialization details.

- Distinguish from [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge uses an already goal-matching lemma/trait contract; opaque route must expose a definition through open counterpart/connector/helper.

- Distinguish from [existing-roundtrip-proof-mode](existing-roundtrip-proof-mode.md): Roundtrip route invokes an existing proof-mode roundtrip fact before a value is moved; opaque route obtains structural facts for closed/nondecreasing definitions.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge uses an already goal-matching lemma/trait contract; opaque route must expose a definition through open counterpart/connector/helper.

- Related [existing-roundtrip-proof-mode](existing-roundtrip-proof-mode.md): Roundtrip route invokes an existing proof-mode roundtrip fact before a value is moved; opaque route obtains structural facts for closed/nondecreasing definitions.

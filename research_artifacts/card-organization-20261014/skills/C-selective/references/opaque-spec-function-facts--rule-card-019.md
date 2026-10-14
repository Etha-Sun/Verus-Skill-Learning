# Facts about opaque/nondecreasing spec functions via open or recursive counterparts

## Scope

- Consult when: Need a length, body, or equality fact about a closed/opaque/nondecreasing spec function or wrapper
- Consult when: Direct reveal or length assertion is rejected or fails
- Consult when: An open counterpart/connector, fixed-width lemma, or recursive proof helper can expose the body
- Not for: Direct revealing is supported or an existing direct lemma closes the goal
- Not for: Required open counterpart/connector/fixed-width lemma is unavailable

<a id="rule-card-019"></a>
## Fuel reveal rejected for a nonrecursive spec wrapper

Source cards: card-019

**Trigger:** An attempt to unfold a spec function with no decreasing clause using fuel-based revealing is rejected.

**Action:** Introduce a recursive proof helper that directly reasons about the underlying fold body, then in the original required proof call that helper and assert definitional equality between the required wrapper and the underlying fold expression used in the helper.

**Why:** Fuel-based revealing requires a decreasing clause that the wrapper lacks; asserting definitional equality with the open spec body is sufficient to transfer the helper's result to the required goal.

**Validate:** Rerun Verus after replacing the revealing call with the helper plus equality assertion; expect all functions verified. Then run the safety comparison and expect a zero exit.

**Avoid when:** The target spec function already supports direct revealing with a decreasing clause, or the body can be proven directly in the original function without a wrapper.

- Distinguish from [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge uses an already goal-matching lemma/trait contract; opaque route must expose a definition through open counterpart/connector/helper.

- Distinguish from [existing-roundtrip-proof-mode](existing-roundtrip-proof-mode.md): Roundtrip route invokes an existing proof-mode roundtrip fact before a value is moved; opaque route obtains structural facts for closed/nondecreasing definitions.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge uses an already goal-matching lemma/trait contract; opaque route must expose a definition through open counterpart/connector/helper.

- Related [existing-roundtrip-proof-mode](existing-roundtrip-proof-mode.md): Roundtrip route invokes an existing proof-mode roundtrip fact before a value is moved; opaque route obtains structural facts for closed/nondecreasing definitions.

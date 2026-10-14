# Facts about opaque/nondecreasing spec functions via open or recursive counterparts

## Scope

- Consult when: Need a length, body, or equality fact about a closed/opaque/nondecreasing spec function or wrapper
- Consult when: Direct reveal or length assertion is rejected or fails
- Consult when: An open counterpart/connector, fixed-width lemma, or recursive proof helper can expose the body
- Not for: Direct revealing is supported or an existing direct lemma closes the goal
- Not for: Required open counterpart/connector/fixed-width lemma is unavailable

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 019 concerns rejected fuel reveal on a nondecreasing wrapper. 021 concerns a closed length fact with an open counterpart/connector; 053 is the length-prefixed injectivity case with a fixed-width length/round-trip lemma. Length subgoals can overlap; check which library facts actually exist.

<a id="rule-card-019"></a>
- [rule-card-019](opaque-spec-function-facts--rule-card-019.md): Fuel reveal rejected for a spec wrapper.
  - When: Fuel-based revealing is rejected for a spec function without a decreasing clause.
  - Avoid: Direct revealing is supported or the original function needs no wrapper.

<a id="rule-card-021"></a>
- [rule-card-021](opaque-spec-function-facts--rule-card-021.md): Closed serialization length with an open counterpart.
  - When: A needed closed-function length fact is unavailable directly but the library has an open counterpart and connector.
  - Avoid: No open counterpart/connector or the spec avoids encoding details.

<a id="rule-card-053"></a>
- [rule-card-053](opaque-spec-function-facts--rule-card-053.md): Header/payload injectivity with a fixed-width encoding lemma.
  - When: Length-prefixed injectivity needs header/sequence facts and the library supplies a fixed-width length and decode-round-trip lemma.
  - Avoid: No fixed-width header or no such installed encoding lemma.

Read: `python3 reference_read.py opaque-spec-function-facts --rules ID [ID ...]`

Whole reference: `python3 reference_read.py opaque-spec-function-facts --full` or [opaque-spec-function-facts--full.md](opaque-spec-function-facts--full.md).

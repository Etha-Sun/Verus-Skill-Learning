# Sequence equality by length and pointwise element facts

## Scope

- Consult when: Goal is equality of two sequence expressions and direct assertion fails
- Consult when: Extensional length and elementwise reasoning can establish both directions
- Not for: Checker already discharges sequence equality directly
- Not for: Installed environment lacks usable extensional length/index laws

## Rules

- [Retain original card-067](#seq-ext-eq-verbatim-card-067)

<a id="seq-ext-eq-verbatim-card-067"></a>
## Retain original card-067

Source cards: card-067

**Trigger:** You need to prove equality of two sequence expressions, especially an equivalence that holds after adding the same suffix to both sides, and the proof body is empty or the equality is not discharging.
**Action:** Prove the two implications separately. For each implication, first establish length equality from the concatenation length laws, then prove that the two sequences agree at every valid index by splitting an index at the boundary between the original prefix and the appended suffix. For the reverse implication, recover prefix length equality from equality of the concatenated lengths, then relate each original element through the concatenation index laws. Close sequence equality with the available extensional equality mechanism, using a fully qualified library path if needed.
**Why:** Sequence equality is justified by equal lengths plus equal elements, and the prover often cannot infer the full elementwise fact without explicit index case analysis. The shared suffix supplies matching suffix elements, and equality of the concatenated lengths yields equality of the original lengths.
**Validate:** Re-run Verus after adding the facts. If a length assertion still fails, add the intermediate equalities that expose concatenation length facts before the failing assertion. Finish with the proof-only safety comparison and require both checks to pass.
**Avoid when:** The checker already discharges sequence equality without pointwise facts, or the sequence type does not have usable extensional length and index laws in the installed environment.

## Conditional links

- When After resolving the qualified path, when the closure still requires the explicit length and elementwise sequence-equality premises.: [proof-helper-qualified-path/sequence-equality-closure-qualified-path](proof-helper-qualified-path.md#sequence-equality-closure-qualified-path)
- When Once the fixed-width header contract is established, when the remaining header and payload sequence equality needs length and pointwise element facts.: [opaque-spec-function-facts/rule-card-053](opaque-spec-function-facts.md#rule-card-053)

- Distinguish from [set-equality-membership-witness](set-equality-membership-witness.md): Set equality concerns set membership witnesses; sequence equality concerns equal lengths and equal indexed elements.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Set equality concerns set membership witnesses; sequence equality concerns equal lengths and equal indexed elements.

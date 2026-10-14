# Constructor case analysis for view/marshalability equality

## Scope

- Consult when: Goal is equal abstract views imply equal marshalability
- Consult when: No packaged view-equal/trait bridge exists or packaged route cannot instantiate
- Consult when: Constructor cases expose field-level view equalities and per-field lemmas
- Not for: Packaged bridge already discharges the obligation
- Not for: Mismatch contradiction would rely on unestablished universal distinctness

## Rules

- [Constructor case analysis for view/marshalability equality](#retain-card-044-constructor-case)

<a id="retain-card-044-constructor-case"></a>
## Constructor case analysis for view/marshalability equality

Source cards: card-044

**Trigger:** The packaged existing-lemma chain fails to instantiate, or no view-equal specification bridge is available, for a proof that equal abstract views imply equal marshalability.
**Action:** Perform constructor case analysis over both values. Mismatched constructors close by contradiction because their abstract view forms are distinct under the equal-view premise. Matching constructors derive field-level view equalities from the record equality, invoke the per-field equal-view and equal-serialization lemmas, and then assert the resulting whole-value marshalability equality, including any serialized-length components.
**Why:** Constructor case analysis exposes the field equalities that the derivation requires, allowing the existing per-field lemmas to compose into the whole-value predicate.
**Validate:** Run the checker; success is one verified function and zero errors. Then run the proof-only comparison and confirm no executable difference.
**Avoid when:** If the mismatch contradiction relies on assuming distinct view constructors that have not been established by the view definition, avoid using a universal distinctness claim; only split cases and derive the contradiction from the concrete view equations for the involved variants.

## Conditional links

- When When the packaged view-equal/trait chain cannot be instantiated and explicit constructor case analysis is needed.: [direct-existing-lemma-bridge/original-card-043](direct-existing-lemma-bridge.md#original-card-043)
- When When the trait bridge is exposed but structural view equality remains open and constructor case splitting is needed.: [direct-existing-lemma-bridge/original-card-003](direct-existing-lemma-bridge.md#original-card-003)

- Distinguish from [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge first tries packaged declaration/trait route; this family is the fallback explicit case analysis.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge first tries packaged declaration/trait route; this family is the fallback explicit case analysis.

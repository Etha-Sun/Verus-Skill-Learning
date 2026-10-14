# Eventual/existential temporal index witness bridging

## Scope

- Consult when: Goal is eventual or existential temporal obligation with an existing raw/action occurrence or witness
- Consult when: Lifted eventual/post-state assertion fails despite that witness
- Consult when: A concrete natural index or spec-level choice can expose the occurrence
- Not for: No occurrence or pointwise action-to-state implication exists
- Not for: Needed suffix/offset arithmetic cannot be established

<a id="card-009-verbatim"></a>
## Original card-009: bridge raw witness to nested-suffix eventual satisfaction

Source cards: card-009

**Trigger:** The proof already has an existential witness for a raw state predicate at an absolute shifted index, but the assertion that the lifted state predicate eventually holds on the current suffix still fails.

**Action:** State a pointwise implication for every natural index: if the raw state predicate holds at the current offset plus that index, then the lifted state predicate holds on the nested suffix that advances the current suffix by that index. Prove this implication inside the proof block by relating the nested suffix head to the offset-plus-index state and using arithmetic equality. Then derive the existential lifted-suffix form and close the eventual assertion.

**Why:** The eventual operator unfolds to an existential over suffixes. The solver needs an intermediate implication matching the raw absolute index to the head of the corresponding nested suffix before it can close the temporal obligation.

**Validate:** Rerun Verus and expect the eventual lifted-state assertion to clear and the proof to verify with zero errors. Run the safety comparison tool afterward.

**Avoid when:** The needed arithmetic relation between the offset, witness, and suffix head cannot be established, or the lifted predicate cannot be unfolded with the available state view. Do not add a pointwise implication whose premise does not match the existing witness.

- Distinguish from [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): This route bridges time/state indices for a known occurrence; existential-witness-lifting handles message/witness predicates with helper lemmas.

- Related [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): This eventual-witness-index-bridge route bridges time/state indices for a known occurrence or an existing shifted raw-state witness, or obtains an index via spec-level choice. Temporal-existential-witness-lifting instead selects message-like witnesses and lifts per-witness helper facts.

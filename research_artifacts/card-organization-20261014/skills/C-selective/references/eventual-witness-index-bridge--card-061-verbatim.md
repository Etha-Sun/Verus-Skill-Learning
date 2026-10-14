# Eventual/existential temporal index witness bridging

## Scope

- Consult when: Goal is eventual or existential temporal obligation with an existing raw/action occurrence or witness
- Consult when: Lifted eventual/post-state assertion fails despite that witness
- Consult when: A concrete natural index or spec-level choice can expose the occurrence
- Not for: No occurrence or pointwise action-to-state implication exists
- Not for: Needed suffix/offset arithmetic cannot be established

<a id="card-061-verbatim"></a>
## Original card-061: use spec-level choice with valid trigger for reachability witness

Source cards: card-061

**Trigger:** A temporal proof branch reduces to an existential reachability obligation and requires a witness index, but constructing the index manually is difficult. **Action:** Use the available spec-level choice construct to obtain a witness from the existential property. Ensure the chosen condition has an explicit trigger term that is a function application or field access rather than a bare equality, then use the witness property to relocate the next-state application and close the eventual obligation with the witness lemma. **Why:** The choice construct provides a concrete index satisfying the existential, and the trigger makes the choice quantifier well-formed. This avoids guessing arithmetic witness positions. **Validate:** Re-run Verus; the branch should verify and any previous witness-precondition failure should clear. Remove any temporary probe functions before finishing. **Avoid when:** The existential does not actually hold, or the chosen witness property is not sufficient for the next-step reasoning; choice cannot replace a missing premise.

- Distinguish from [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): This route bridges time/state indices for a known occurrence; existential-witness-lifting handles message/witness predicates with helper lemmas.

- Related [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): This eventual-witness-index-bridge route bridges time/state indices for a known occurrence or an existing shifted raw-state witness, or obtains an index via spec-level choice. Temporal-existential-witness-lifting instead selects message-like witnesses and lifts per-witness helper facts.

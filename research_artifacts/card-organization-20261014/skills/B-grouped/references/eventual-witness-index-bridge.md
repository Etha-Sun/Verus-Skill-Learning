# Eventual/existential temporal index witness bridging

## Scope

- Consult when: Goal is eventual or existential temporal obligation with an existing raw/action occurrence or witness
- Consult when: Lifted eventual/post-state assertion fails despite that witness
- Consult when: A concrete natural index or spec-level choice can expose the occurrence
- Not for: No occurrence or pointwise action-to-state implication exists
- Not for: Needed suffix/offset arithmetic cannot be established

## Rules

- [Original card-008: choose concrete natural index for eventual action occurrence](#card-008-verbatim)
- [Original card-009: bridge raw witness to nested-suffix eventual satisfaction](#card-009-verbatim)
- [Original card-061: use spec-level choice with valid trigger for reachability witness](#card-061-verbatim)

<a id="card-008-verbatim"></a>
## Original card-008: choose concrete natural index for eventual action occurrence

Source cards: card-008

**Trigger:** A generic helper has established that an action eventually fires after every point, but the desired existential post-state does not follow. The verifier reports that the post-state existence or the lifted eventual-state assertion failed.

**Action:** From the eventual action fact on a suffix, choose a concrete natural index for the action occurrence. Rewrite that lifted action occurrence into an action on the underlying consecutive states at the shifted index, then instantiate the pointwise implication that action plus always-true preconditions yields the post-state.

**Why:** Choosing the witness exposes a concrete index that the solver can use to instantiate quantified implications. Without this step, the occurrence may remain hidden inside the temporal existential and prevent synthesis of a post-state witness.

**Validate:** Rerun Verus and expect the failed post-state existential to clear and the full proof to verify with zero errors. Run the safety comparison tool afterward.

**Avoid when:** Trigger restrictions make the chosen occurrence unusable, or no pointwise action-to-post implication is available. Do not choose a witness and then assert unsupported consequences.

<a id="card-009-verbatim"></a>
## Original card-009: bridge raw witness to nested-suffix eventual satisfaction

Source cards: card-009

**Trigger:** The proof already has an existential witness for a raw state predicate at an absolute shifted index, but the assertion that the lifted state predicate eventually holds on the current suffix still fails.

**Action:** State a pointwise implication for every natural index: if the raw state predicate holds at the current offset plus that index, then the lifted state predicate holds on the nested suffix that advances the current suffix by that index. Prove this implication inside the proof block by relating the nested suffix head to the offset-plus-index state and using arithmetic equality. Then derive the existential lifted-suffix form and close the eventual assertion.

**Why:** The eventual operator unfolds to an existential over suffixes. The solver needs an intermediate implication matching the raw absolute index to the head of the corresponding nested suffix before it can close the temporal obligation.

**Validate:** Rerun Verus and expect the eventual lifted-state assertion to clear and the proof to verify with zero errors. Run the safety comparison tool afterward.

**Avoid when:** The needed arithmetic relation between the offset, witness, and suffix head cannot be established, or the lifted predicate cannot be unfolded with the available state view. Do not add a pointwise implication whose premise does not match the existing witness.

<a id="card-061-verbatim"></a>
## Original card-061: use spec-level choice with valid trigger for reachability witness

Source cards: card-061

**Trigger:** A temporal proof branch reduces to an existential reachability obligation and requires a witness index, but constructing the index manually is difficult. **Action:** Use the available spec-level choice construct to obtain a witness from the existential property. Ensure the chosen condition has an explicit trigger term that is a function application or field access rather than a bare equality, then use the witness property to relocate the next-state application and close the eventual obligation with the witness lemma. **Why:** The choice construct provides a concrete index satisfying the existential, and the trigger makes the choice quantifier well-formed. This avoids guessing arithmetic witness positions. **Validate:** Re-run Verus; the branch should verify and any previous witness-precondition failure should clear. Remove any temporary probe functions before finishing. **Avoid when:** The existential does not actually hold, or the chosen witness property is not sufficient for the next-step reasoning; choice cannot replace a missing premise.

- Distinguish from [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): This route bridges time/state indices for a known occurrence; existential-witness-lifting handles message/witness predicates with helper lemmas.

- Related [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): This eventual-witness-index-bridge route bridges time/state indices for a known occurrence or an existing shifted raw-state witness, or obtains an index via spec-level choice. Temporal-existential-witness-lifting instead selects message-like witnesses and lifts per-witness helper facts.

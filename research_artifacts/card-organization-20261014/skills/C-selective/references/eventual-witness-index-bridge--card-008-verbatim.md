# Eventual/existential temporal index witness bridging

## Scope

- Consult when: Goal is eventual or existential temporal obligation with an existing raw/action occurrence or witness
- Consult when: Lifted eventual/post-state assertion fails despite that witness
- Consult when: A concrete natural index or spec-level choice can expose the occurrence
- Not for: No occurrence or pointwise action-to-state implication exists
- Not for: Needed suffix/offset arithmetic cannot be established

<a id="card-008-verbatim"></a>
## Original card-008: choose concrete natural index for eventual action occurrence

Source cards: card-008

**Trigger:** A generic helper has established that an action eventually fires after every point, but the desired existential post-state does not follow. The verifier reports that the post-state existence or the lifted eventual-state assertion failed.

**Action:** From the eventual action fact on a suffix, choose a concrete natural index for the action occurrence. Rewrite that lifted action occurrence into an action on the underlying consecutive states at the shifted index, then instantiate the pointwise implication that action plus always-true preconditions yields the post-state.

**Why:** Choosing the witness exposes a concrete index that the solver can use to instantiate quantified implications. Without this step, the occurrence may remain hidden inside the temporal existential and prevent synthesis of a post-state witness.

**Validate:** Rerun Verus and expect the failed post-state existential to clear and the full proof to verify with zero errors. Run the safety comparison tool afterward.

**Avoid when:** Trigger restrictions make the chosen occurrence unusable, or no pointwise action-to-post implication is available. Do not choose a witness and then assert unsupported consequences.

- Distinguish from [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): This route bridges time/state indices for a known occurrence; existential-witness-lifting handles message/witness predicates with helper lemmas.

- Related [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): This eventual-witness-index-bridge route bridges time/state indices for a known occurrence or an existing shifted raw-state witness, or obtains an index via spec-level choice. Temporal-existential-witness-lifting instead selects message-like witnesses and lifts per-witness helper facts.

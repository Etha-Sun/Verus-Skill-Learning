# Temporal existential witness lifting and leads-to composition

## Scope

- Consult when: Leads-to or equality temporal formula contains existential message/state predicates
- Consult when: Per-witness helper lemmas or witness-introduction/equality rules exist
- For leads-to: Check the selected rule's per-witness helper premises; card-016 also requires an atomic membership/equality witness source
- For equality (card-033): Check the trusted predicate-equality and witness-introduction rules and witness facts; a per-witness leads-to lemma is not its premise
- Not for: The selected rule's required trusted helpers or witness facts are unavailable

<a id="card-032-verbatim"></a>
## Existential leads-to intermediates with witness-specific helpers; lift witnesses and compose intermediate entailments.

Source cards: card-032

**Trigger:** A temporal leads-to goal has source or intermediate states that contain an existential over messages or other witnesses, while existing helper lemmas prove the property only for one specific witness at a time.

**Action:** Decompose the leads-to goal into intermediate lifted state predicates. For each witness-specific helper lemma, prove the universal fact over witnesses and lift it to the existential with the available existence-introduction rule. Then prove the source existential state implies the lifted witness-specific existential by reasoning pointwise over executions: take the head state, select a concrete witness already present there, and show it satisfies the specific predicate. Apply transitivity, including a final chain from the original source through the intermediate state to the target. Add manual trigger annotations to quantified entailment assertions when Verus requests them.

**Why:** Direct assertions of existential lifting often fail because the solver cannot choose the witness or instantiate the existential. Explicit witness selection gives the solver a concrete term. The final transitivity step is needed because proving each leg independently does not by itself establish the full leads-to postcondition.

**Validate:** Re-run Verus and confirm the target lemma postcondition closes with zero errors, then run the Lynette safety comparison. The successful or unsuccessful traces show that trigger annotations alone only clear a compilation error and do not prove the postcondition until the witness bridges and transitivity step are present.

**Avoid when:** A helper lemma for the per-witness step is not available or cannot be instantiated under the current assumptions. Also avoid asserting that a source existential state entails the lifted existential without a pointwise witness proof, and do not stop after proving the individual legs if the original goal still has an unexecuted final transitivity requirement.

- Distinguish from [eventual-witness-index-bridge](eventual-witness-index-bridge.md): Eventual index route chooses a time occurrence; this route selects message-like witnesses and lifts per-witness facts.

- Related [eventual-witness-index-bridge](eventual-witness-index-bridge.md): Eventual index route chooses a time occurrence; this route selects message-like witnesses and lifts per-witness facts.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Temporal existential witness lifting concerns execution/message existential goals, not membership equality of sets.

- Related [temporal-predicate-equality-pointwise](temporal-predicate-equality-pointwise.md): Existential-witness route chooses message-like witnesses; temporal object equality route uses pointwise entailment and index identities.

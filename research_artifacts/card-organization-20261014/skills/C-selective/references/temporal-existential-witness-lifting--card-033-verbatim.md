# Temporal existential witness lifting and leads-to composition

## Scope

- Consult when: Leads-to or equality temporal formula contains existential message/state predicates
- Consult when: Per-witness helper lemmas or witness-introduction/equality rules exist
- For leads-to: Check the selected rule's per-witness helper premises; card-016 also requires an atomic membership/equality witness source
- For equality (card-033): Check the trusted predicate-equality and witness-introduction rules and witness facts; a per-witness leads-to lemma is not its premise
- Not for: The selected rule's required trusted helpers or witness facts are unavailable

<a id="card-033-verbatim"></a>
## Existential temporal equality with available equality/witness rules; prove both entailments and introduce witnesses explicitly.

Source cards: card-033

**Trigger:** Two temporal predicates must be proved equal, where at least one side is an existential temporal predicate combined with another predicate, and the source context provides a predicate-equality rule and a witness-introduction rule.

**Action:** Reduce the equality to mutual entailment. Prove each entailment for an arbitrary execution by branching on whether the antecedent holds. When a goal is an existential temporal predicate, select a concrete witness and expose the conjuncts that the witness satisfies, then use the existing witness-introduction rule to obtain the existential instead of asserting the existential directly. Finish with the predicate-equality rule.

**Why:** A bare assertion of an existential predicate can fail because the existential trigger is a combined term that never appears as a ground term from the separate conjuncts. The witness-introduction rule requires exactly a concrete witness and its predicate facts, so it closes the existential reliably. Mutual entailment is the appropriate reduction because the equality rule consumes entailments in both directions.

**Validate:** Run Verus and confirm the proof function verifies with zero errors, then run Lynette. The failure evidence shows a bare existential assertion in the reverse direction failing, and the repaired versions passing only after the witness-introduction rule was applied.

**Avoid when:** The relevant predicate-equality or witness-introduction rule is not already trusted in the supplied source. Also avoid relying on an implication assertion to enter the antecedent into scope when the Verus version warns otherwise; use an explicit case-split in that situation.

- Distinguish from [eventual-witness-index-bridge](eventual-witness-index-bridge.md): Eventual index route chooses a time occurrence; this route selects message-like witnesses and lifts per-witness facts.

- Related [eventual-witness-index-bridge](eventual-witness-index-bridge.md): Eventual index route chooses a time occurrence; this route selects message-like witnesses and lifts per-witness facts.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Temporal existential witness lifting concerns execution/message existential goals, not membership equality of sets.

- Related [temporal-predicate-equality-pointwise](temporal-predicate-equality-pointwise.md): Existential-witness route chooses message-like witnesses; temporal object equality route uses pointwise entailment and index identities.

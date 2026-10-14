# Temporal existential witness lifting and leads-to composition

## Scope

- Consult when: Leads-to or equality temporal formula contains existential message/state predicates
- Consult when: Per-witness helper lemmas or witness-introduction/equality rules exist
- For leads-to: Check the selected rule's per-witness helper premises; card-016 also requires an atomic membership/equality witness source
- For equality (card-033): Check the trusted predicate-equality and witness-introduction rules and witness facts; a per-witness leads-to lemma is not its premise
- Not for: The selected rule's required trusted helpers or witness facts are unavailable

<a id="card-016-verbatim"></a>
## Message-existential leads-to goal with per-witness lemmas; match predicate templates and existential lifting.

Source cards: card-016

**Trigger:** A temporal logic proof obligation must show that one existential state condition leads to another, and trusted per-witness lemmas already relate the corresponding individual messages but the verifier cannot connect the quantified statement-level conditions.

**Action:** Define predicate templates over a witness that exactly match the trusted lemma postconditions. For each witness, discharge the per-witness leads-to obligation by calling the trusted lemma under a forall assertion with an explicit trigger on the temporal entailment expression. Lift these per-witness obligations to an existential temporal operator. Then bridge the source existential state predicate to that lifted operator by proving, for every execution under an implication that assumes the antecedent, that a witness can be chosen from an atomic in-flight membership or pending-request equality relation and satisfies the per-witness template. Compose the resulting leads-to facts with entailment-to-leads-to conversion and transitivity.

**Why:** The verifier does not automatically distribute existential witnesses through entailment; explicit witness selection exposes the needed instance. The implication form makes the antecedent available inside the proof, and explicit triggers avoid trigger inference failures on the witness quantifier.

**Validate:** Rerun Verus after adding the bridge proofs; the previously failing entailment preconditions or bridge assertions should clear, and the final run should report all functions verified with no errors. Then run the proof-safety comparison and expect a zero exit.

**Avoid when:** No trusted per-witness lemma exists, or the witness cannot be selected from an atomic state membership or equality relationship; relying only on composed high-level predicates in the witness choice can still fail or leave triggers unresolved.

- Distinguish from [eventual-witness-index-bridge](eventual-witness-index-bridge.md): Eventual index route chooses a time occurrence; this route selects message-like witnesses and lifts per-witness facts.

- Related [eventual-witness-index-bridge](eventual-witness-index-bridge.md): Eventual index route chooses a time occurrence; this route selects message-like witnesses and lifts per-witness facts.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Temporal existential witness lifting concerns execution/message existential goals, not membership equality of sets.

- Related [temporal-predicate-equality-pointwise](temporal-predicate-equality-pointwise.md): Existential-witness route chooses message-like witnesses; temporal object equality route uses pointwise entailment and index identities.

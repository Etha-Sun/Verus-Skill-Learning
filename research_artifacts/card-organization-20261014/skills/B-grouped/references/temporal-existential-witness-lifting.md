# Temporal existential witness lifting and leads-to composition

## Scope

- Consult when: Leads-to or equality temporal formula contains existential message/state predicates
- Consult when: Per-witness helper lemmas or witness-introduction/equality rules exist
- Consult when: A concrete witness can be selected from an atomic state relation
- Not for: No trusted per-witness lemma exists
- Not for: Witness cannot be selected from atomic membership/state equality

## Rules

- [Message-existential leads-to goal with per-witness lemmas; match predicate templates and existential lifting.](#card-016-verbatim)
- [Existential leads-to intermediates with witness-specific helpers; lift witnesses and compose intermediate entailments.](#card-032-verbatim)
- [Existential temporal equality with available equality/witness rules; prove both entailments and introduce witnesses explicitly.](#card-033-verbatim)

<a id="card-016-verbatim"></a>
## Message-existential leads-to goal with per-witness lemmas; match predicate templates and existential lifting.

Source cards: card-016

**Trigger:** A temporal logic proof obligation must show that one existential state condition leads to another, and trusted per-witness lemmas already relate the corresponding individual messages but the verifier cannot connect the quantified statement-level conditions.

**Action:** Define predicate templates over a witness that exactly match the trusted lemma postconditions. For each witness, discharge the per-witness leads-to obligation by calling the trusted lemma under a forall assertion with an explicit trigger on the temporal entailment expression. Lift these per-witness obligations to an existential temporal operator. Then bridge the source existential state predicate to that lifted operator by proving, for every execution under an implication that assumes the antecedent, that a witness can be chosen from an atomic in-flight membership or pending-request equality relation and satisfies the per-witness template. Compose the resulting leads-to facts with entailment-to-leads-to conversion and transitivity.

**Why:** The verifier does not automatically distribute existential witnesses through entailment; explicit witness selection exposes the needed instance. The implication form makes the antecedent available inside the proof, and explicit triggers avoid trigger inference failures on the witness quantifier.

**Validate:** Rerun Verus after adding the bridge proofs; the previously failing entailment preconditions or bridge assertions should clear, and the final run should report all functions verified with no errors. Then run the proof-safety comparison and expect a zero exit.

**Avoid when:** No trusted per-witness lemma exists, or the witness cannot be selected from an atomic state membership or equality relationship; relying only on composed high-level predicates in the witness choice can still fail or leave triggers unresolved.

<a id="card-032-verbatim"></a>
## Existential leads-to intermediates with witness-specific helpers; lift witnesses and compose intermediate entailments.

Source cards: card-032

**Trigger:** A temporal leads-to goal has source or intermediate states that contain an existential over messages or other witnesses, while existing helper lemmas prove the property only for one specific witness at a time.

**Action:** Decompose the leads-to goal into intermediate lifted state predicates. For each witness-specific helper lemma, prove the universal fact over witnesses and lift it to the existential with the available existence-introduction rule. Then prove the source existential state implies the lifted witness-specific existential by reasoning pointwise over executions: take the head state, select a concrete witness already present there, and show it satisfies the specific predicate. Apply transitivity, including a final chain from the original source through the intermediate state to the target. Add manual trigger annotations to quantified entailment assertions when Verus requests them.

**Why:** Direct assertions of existential lifting often fail because the solver cannot choose the witness or instantiate the existential. Explicit witness selection gives the solver a concrete term. The final transitivity step is needed because proving each leg independently does not by itself establish the full leads-to postcondition.

**Validate:** Re-run Verus and confirm the target lemma postcondition closes with zero errors, then run the Lynette safety comparison. The successful or unsuccessful traces show that trigger annotations alone only clear a compilation error and do not prove the postcondition until the witness bridges and transitivity step are present.

**Avoid when:** A helper lemma for the per-witness step is not available or cannot be instantiated under the current assumptions. Also avoid asserting that a source existential state entails the lifted existential without a pointwise witness proof, and do not stop after proving the individual legs if the original goal still has an unexecuted final transitivity requirement.

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

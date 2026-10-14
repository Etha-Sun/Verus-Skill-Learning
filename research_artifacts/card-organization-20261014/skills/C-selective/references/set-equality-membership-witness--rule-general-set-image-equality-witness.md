# Set equality by membership extensionality and witnesses

## Scope

- Consult when: Goal is equality of sets/set images or a sequence-set view after removal
- Consult when: No direct matching library lemma
- Consult when: Membership equivalence and witness indices are required
- Not for: Direct library lemma already applies with available premises
- Not for: Membership extensionality is not the missing step

<a id="rule-general-set-image-equality-witness"></a>
## Set/image equality by membership extensionality with reverse witnesses

Source cards: card-002

**Trigger:** The proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment.
**Action:** Establish set equality through pointwise membership equivalence. For the forward direction, derive membership in the image union from membership in either image using union and image definitions. For the reverse direction, when image membership is assumed on one side, introduce a chosen witness satisfying the corresponding source membership and mapping relation; prove the witness belongs to the union; then derive the union image membership and obtain the contradiction. If the verifier warns about low-confidence triggers for the quantified equivalence, accept the automatic trigger or annotate the equivalence to give the solver reliable membership triggers.
**Why:** The reverse direction requires exposing the existential witness because merely asserting union-image membership does not give the solver enough information. The chosen witness connects the image definition to union membership. Trigger annotation can suppress a warning after the logical witness step succeeds, but the success depends on that witness.
**Validate:** Run the verifier after adding the witness step and confirm zero errors; then run the proof-safety comparison. Confirm no assumptions or specification changes were introduced.
**Avoid when:** A directly applicable library lemma proves the same obligation and its premises hold, because manual witness reasoning is then avoidable. Also avoid assuming after a successful proof that the trigger annotation alone was responsible for discharging the obligation; it may only have suppressed a warning.

- Distinguish from [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): Temporal existential witness lifting concerns execution/message existential goals, not membership equality of sets.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Use the direct-bridge route only when an existing lemma itself closes the algebraic goal; otherwise set equality requires membership extensionality and explicit witnesses.

- Related [sequence-extensional-equality](sequence-extensional-equality.md): Set equality concerns set membership and witnesses; sequence equality concerns equal lengths and equal indexed elements.

- Related [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): Temporal existential witness lifting concerns execution/message existential goals, not membership equality of sets.

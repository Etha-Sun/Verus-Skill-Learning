# Set equality by membership extensionality and witnesses

## Scope

- Consult when: Goal is equality of sets/set images or a sequence-set view after removal
- Consult when: No direct matching library lemma
- Consult when: Membership equivalence and witness indices are required
- Not for: Direct library lemma already applies with available premises
- Not for: Membership extensionality is not the missing step

<a id="rule-no-duplicate-sequence-removal-set-equality"></a>
## Duplicate-free sequence-removal view equality with index-shift witnesses

Source cards: card-049

**Trigger:** A proof obligation asks to show that the set view of a sequence after removing an index equals the set view of the original sequence with the element at that index removed, and the sequence is known to have no duplicates.
**Action:** Prove the set equality through membership extensionality. For an arbitrary element, establish membership equivalence by taking a witness index and splitting on whether that index precedes or follows the removed index; map the witness back and forth using the sequence removal index-shift relation, and use the no-duplicates fact to rule out the removed element appearing elsewhere. Then lift the elementwise equivalence to set equality using an existing vstd set-extensionality proof mechanism. In the containing function, obtain no-duplicates for the old sequence from its validity fact, apply the lemma to the old sequence and cast index, and chain the vector removal facts plus the returned element equality to close the postcondition.
**Why:** The solver already has the sequence-level equality after the vector removal, but it does not automatically connect the shorter sequence's set view to the original set after removing the indexed element; the no-duplicates assumption is the missing logical premise that prevents the removed element from recurring.
**Validate:** Run Verus and confirm the postcondition is discharged and the whole file verifies. Then run the proof-only safety comparison; in the supplied traces this approach verifies with two or three functions and passes Lynette after any proof-only import or macro issue is removed.
**Avoid when:** The sequence may contain duplicates or the removed element can occur at another index, because the set equality is then false. Also do not leave an empty universal membership assertion; the witness case analysis is the substantive part of the proof.

- Distinguish from [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): Temporal existential witness lifting concerns execution/message existential goals, not membership equality of sets.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Use the direct-bridge route only when an existing lemma itself closes the algebraic goal; otherwise set equality requires membership extensionality and explicit witnesses.

- Related [sequence-extensional-equality](sequence-extensional-equality.md): Set equality concerns set membership and witnesses; sequence equality concerns equal lengths and equal indexed elements.

- Related [temporal-existential-witness-lifting](temporal-existential-witness-lifting.md): Temporal existential witness lifting concerns execution/message existential goals, not membership equality of sets.

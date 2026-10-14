# While-loop termination measures and invariant carrying

## Scope

- Consult when: A while loop lacks decreases, loses entry assumptions in its body, or fails packet-prefix set/validity obligations
- Consult when: Remaining iterations or carried invariants can discharge the obligation
- Not for the counting-termination rule: No strictly decreasing numeric measure of the stated form
- Not for carrying an unchanged assumption: It is not preserved on every iteration; this does not exclude the packet rule's evolving inductive relation

## Rules

- [While-loop termination measure for counting loops](#loop-counting-termination-measure)
- [Carrying function-entry assumptions into a loop body](#loop-body-inherited-assumption-invariant)
- [Packet-prefix loop inductive set invariant](#packet-prefix-set-invariant)

<a id="loop-counting-termination-measure"></a>
## While-loop termination measure for counting loops

Source cards: card-035

**Trigger:** Verus reports that a while loop must have a decreases clause, while the loop counter starts at zero and increments until it reaches a collection length.
**Action:** Add a termination measure equal to the number of iterations remaining, written as the collection length minus the current index, and include an invariant that the index remains within the collection bounds.
**Why:** Giving Verus a strictly decreasing measure discharges the termination obligation and lets verification proceed to the body's proof obligations instead of stopping at the loop header.
**Validate:** Rerun Verus; the missing-decreases diagnostic should disappear and any next failure should move into the loop body or its calls.
**Avoid when:** The loop termination depends on state that is not captured by a simple numeric counter decreasing toward a bound, or when the expression used as the measure is not actually decreasing on every path.

<a id="loop-body-inherited-assumption-invariant"></a>
## Carrying function-entry assumptions into a loop body

Source cards: card-036

**Trigger:** After termination is accepted, a call inside a loop fails a precondition or assertion that depends on the enclosing function's assumptions, even though those assumptions were true at function entry.
**Action:** Add the needed function preconditions as loop invariants. If they mention entry-time state, first snapshot that state into ghost constants and include invariants linking the current state to the entry snapshot.
**Why:** In the observed Verus behavior, the loop body sees loop invariants rather than the function's requires clauses, so facts that must justify a call have to be restated inside the invariant list.
**Validate:** Rerun Verus; the call precondition should clear or shift to a more specific per-index or arithmetic obligation.
**Avoid when:** The relevant assumption is not actually preserved on every iteration, because the loop modifies the state it describes; in that case, a weaker per-iteration invariant or a separate induction argument is needed.

<a id="packet-prefix-set-invariant"></a>
## Packet-prefix loop inductive set invariant

Source cards: card-041

**Trigger:** A while loop over an unapproved prefix mutates an output packet sequence by appending one element per iteration, and after adding a termination measure the verifier still reports that the final set-equality postcondition, a loop-body invariant, or a nested match arm fail.
**Action:** Add an inductive invariant equating the emitted packet views as a set to the initial emitted set plus the abstract unapproved prefix up to the current position. Carry every pre-loop fact used in the body as an invariant, because a loop body does not automatically inherit function preconditions or pre-loop assertions. Capture abstract source and destination in ghost variables before any executable binding shadows a parameter. In each iteration establish that the current element is a message and has the required validity properties, then use the existing lemmas that extend the abstract prefix by one element and relate sequence append to set insertion to advance the invariant from the current index to the next.
**Why:** The missing induction is the set equation connecting the appended sequence to the abstract prefix; without it the final postcondition is unreachable. The needed pre-loop facts disappear inside the body, so the invariant block is the only reliable channel for carrying them into the loop.
**Validate:** Run the checker after adding the invariant and body steps; success is all functions verified and zero errors. Then run the proof-only comparison. If the comparison fails, inspect whether any executable statement or local name changed and restrict all changes to ghost or proof text.
**Avoid when:** When the body still cannot derive the current element's validity from the carried invariants, do not keep repeating the same assertion or the same lemma call; instead expose the missing field or record relation through an explicit invariant or case split, and determine whether the failure is a missing premise rather than a syntax problem.

- Distinguish from [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

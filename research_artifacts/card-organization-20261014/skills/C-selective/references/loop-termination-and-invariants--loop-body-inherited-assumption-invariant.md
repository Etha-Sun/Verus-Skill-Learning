# While-loop termination measures and invariant carrying

## Scope

- Consult when: A while loop lacks decreases, loses entry assumptions in its body, or fails packet-prefix set/validity obligations
- Consult when: Remaining iterations or carried invariants can discharge the obligation
- Not for the counting-termination rule: No strictly decreasing numeric measure of the stated form
- Not for carrying an unchanged assumption: It is not preserved on every iteration; this does not exclude the packet rule's evolving inductive relation

<a id="loop-body-inherited-assumption-invariant"></a>
## Carrying function-entry assumptions into a loop body

Source cards: card-036

**Trigger:** After termination is accepted, a call inside a loop fails a precondition or assertion that depends on the enclosing function's assumptions, even though those assumptions were true at function entry.
**Action:** Add the needed function preconditions as loop invariants. If they mention entry-time state, first snapshot that state into ghost constants and include invariants linking the current state to the entry snapshot.
**Why:** In the observed Verus behavior, the loop body sees loop invariants rather than the function's requires clauses, so facts that must justify a call have to be restated inside the invariant list.
**Validate:** Rerun Verus; the call precondition should clear or shift to a more specific per-index or arithmetic obligation.
**Avoid when:** The relevant assumption is not actually preserved on every iteration, because the loop modifies the state it describes; in that case, a weaker per-iteration invariant or a separate induction argument is needed.

- Distinguish from [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

# While-loop termination measures and invariant carrying

## Scope

- Consult when: A while loop lacks decreases, loses entry assumptions in its body, or fails packet-prefix set/validity obligations
- Consult when: Remaining iterations or carried invariants can discharge the obligation
- Not for the counting-termination rule: No strictly decreasing numeric measure of the stated form
- Not for carrying an unchanged assumption: It is not preserved on every iteration; this does not exclude the packet rule's evolving inductive relation

<a id="loop-counting-termination-measure"></a>
## While-loop termination measure for counting loops

Source cards: card-035

**Trigger:** Verus reports that a while loop must have a decreases clause, while the loop counter starts at zero and increments until it reaches a collection length.
**Action:** Add a termination measure equal to the number of iterations remaining, written as the collection length minus the current index, and include an invariant that the index remains within the collection bounds.
**Why:** Giving Verus a strictly decreasing measure discharges the termination obligation and lets verification proceed to the body's proof obligations instead of stopping at the loop header.
**Validate:** Rerun Verus; the missing-decreases diagnostic should disappear and any next failure should move into the loop body or its calls.
**Avoid when:** The loop termination depends on state that is not captured by a simple numeric counter decreasing toward a bound, or when the expression used as the measure is not actually decreasing on every path.

- Distinguish from [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route instantiates one quantified fact at a concrete element/index; loop route carries multiple iteration facts in the invariant block.

# While-loop termination measures and invariant carrying

## Scope

- Consult when: A while loop lacks decreases, loses entry assumptions in its body, or fails packet-prefix set/validity obligations
- Consult when: Remaining iterations or carried invariants can discharge the obligation
- Not for the counting-termination rule: No strictly decreasing numeric measure of the stated form
- Not for carrying an unchanged assumption: It is not preserved on every iteration; this does not exclude the packet rule's evolving inductive relation

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** Choose the current failing obligation: missing decreases, unavailable entry assumptions, or packet-prefix set/validity reasoning. The packet rule also carries pre-loop facts, so it overlaps the assumption rule. The source does not require reading all three in order.

<a id="loop-counting-termination-measure"></a>
- [loop-counting-termination-measure](loop-termination-and-invariants--loop-counting-termination-measure.md): Counting-loop termination diagnostic.
  - When: A counter increments from zero to a collection length and Verus requests a decreases clause.
  - Avoid: Termination depends on other state or the measure does not decrease on every path.

<a id="loop-body-inherited-assumption-invariant"></a>
- [loop-body-inherited-assumption-invariant](loop-termination-and-invariants--loop-body-inherited-assumption-invariant.md): Function assumptions unavailable inside a loop.
  - When: Termination is accepted but an inner precondition depends on function-entry assumptions.
  - Avoid: The loop modifies relevant state so those assumptions are not preserved.

<a id="packet-prefix-set-invariant"></a>
- [packet-prefix-set-invariant](loop-termination-and-invariants--packet-prefix-set-invariant.md): Packet-prefix append loop with set/validity failure.
  - When: After termination repair, a packet-append prefix loop still fails final set equality, invariant preservation, or a match-arm obligation.
  - Avoid: A different loop relation is required; missing element-validity premises still need proof.

Read: `python3 reference_read.py loop-termination-and-invariants --rules ID [ID ...]`

Whole reference: `python3 reference_read.py loop-termination-and-invariants --full` or [loop-termination-and-invariants--full.md](loop-termination-and-invariants--full.md).

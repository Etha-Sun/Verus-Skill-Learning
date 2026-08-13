# Loop Invariant Design, Break Provenance, and Termination Measures

**Consult when:** A loop reports out-of-bounds or length facts, post-loop universals require a processed-prefix invariant, early break provenance is needed, or a while/recursive proof function needs a decreases measure.

**Do not consult when:** The loop body is fine and the only failure is a set equality or serialization detail after the loop; close those with their own references.

<a id="verus-global-040"></a>

## verus_global_040 — Carry collection length and cursor bounds as loop invariants for safe indexed mutation

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A Verus loop uses an integer cursor to index or remove from a Vec or slice, and Verus reports possible out-of-bounds or cannot prove the current collection length.

**Obstacle:** Verus does not automatically connect the loop cursor and mutation count to the current collection or slice length, so the SMT solver lacks the bounds needed for `vector[index]`, `slice[index]`, or `vector.remove(cursor)`.

**Mechanism:** Strengthen the loop invariant with explicit length relations and cursor bounds: for example, give the slice sequence length as a fixed invariant, constrain the cursor by that length, equate two collection lengths when both are scanned together, or tie a shrinking collection's current length to `old(<vector>).len() - <deleted_count>`.

**Procedure:**
1. Identify every loop-cursor access or removal that needs an in-bounds proof, and any length-changing operation performed in the loop.
2. Add a loop invariant explicitly stating the collection or slice length, or the length relation for shrinking collections.
3. Add bounds on the cursor relative to that declared length so Verus can connect the cursor to the collection size.
4. Keep these invariants minimal and automatically re-establishable after the loop body; use them instead of local in-body bound assertions where possible.

**Why:** These invariants give Verus a direct bridge between the integer cursor and the collection length. The solver can then discharge array-bounds and removal-bounds obligations without reconstructing the history of deletions or slice sizes.

**Check:** The reported out-of-bounds or removal-bounds error should disappear after the length relation and cursor bounds are added, and the invariant should be maintained by the loop body with only simple arithmetic.

**Avoid or stop:**
- Do not assert a length relation that the loop body does not actually maintain.
- Do not add cursor bounds that do not match the loop's real advancement.
- Termination and decreasing measures are outside this skill; add them only if termination is a separate obligation.

<a id="verus-global-041"></a>

## verus_global_041 — Quantified processed-prefix invariants for elementwise and monotonic properties

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A loop scans indices from a lower bound and the postcondition needs a universal fact over all visited or processed elements, such as element equality, view equality, sortedness, or value agreement.

**Obstacle:** After the loop, Verus only knows the final cursor and bounds; it does not accumulate per-element facts unless they are stored in a quantified invariant over the processed prefix.

**Mechanism:** Maintain a quantifier over already processed indices, typically `forall|j: int| <lo> <= j < <cursor> ==> <predicate>(sequence[j], ...)`, together with a cursor-bound invariant. If automatic quantifier instantiation is the bottleneck, annotate the quantifier with `#![auto]` or a sequence-index trigger.

**Procedure:**
1. Define the postcondition as a universal property over the full range that the loop should cover.
2. Add an invariant over the processed prefix using the same predicate that appears in the postcondition.
3. Add a cursor-bound invariant that makes the final cursor cover the complete range on exit.
4. If SMT instantiation fails, annotate the quantifier with an explicit trigger such as `#![auto]` or a sequence-index trigger for the later postcondition.
5. Let the loop exit condition and cursor bound lift the prefix invariant to the full postcondition instead of re-proving the per-element property after the loop.

**Why:** A prefix quantifier encodes that all elements already examined satisfy the desired relation. When the loop exits at the end of the range, the same quantifier is exactly the universal postcondition; the SMT solver only needs to instantiate it for the final range.

**Check:** Post-loop assertions about all indices in the scanned range are discharged without separate per-index proof, and the quantified invariant is verifiable after the first iteration and after each subsequent loop body step.

**Avoid or stop:**
- Do not quantify over indices that the loop has not yet reached unless another invariant maintains those facts.
- The quantifier must be stable across normal iterations; if the body changes elements inside the processed prefix, strengthen or remove it.
- Avoid treating a decreasing termination clause as the main proof mechanism here; termination is a separate obligation outside this family.

<a id="verus-global-042"></a>

## verus_global_042 — Preserve early-exit provenance with ghost state and biconditional loop invariants

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A loop contains a conditional break, and a post-loop proof obligation depends on whether or why the loop exited before exhausting the range.

**Obstacle:** Verus does not retain control-flow history of a break. After the loop it cannot infer from an early-exit cursor that the break condition was true, and executable checks in proof mode cannot reconstruct that past reason.

**Mechanism:** Capture the break reason in ghost state at the exact break site, then maintain it with a strengthened loop invariant that connects the ghost value to the exit condition. The invariant should be biconditional or include the needed direction such as `<cursor> < <len> ==> <ghost_flag>.is_some()` and `<ghost_flag> == Some(<idx>) ==> <break_property_at(<idx>)>`. Do not attempt to re-evaluate the break condition after the loop.

**Procedure:**
1. When first writing a loop with conditional break, introduce a ghost variable to store the break index or condition.
2. Set the ghost variable inside the break branch to the current index and/or the fact that caused the break.
3. Add a loop invariant that keeps the ghost variable stable across normal iterations and records the intended biconditional property: if the loop exits early, the ghost variable is set and the break property holds; if it is set, the property holds.
4. Do not add executable condition checks after the loop or rely on calls that re-evaluate the break condition as proof of the past branch.
5. If the current loop body and control flow cannot support a stable invariant, restructure the loop with a mutable ghost-supported flag or break index rather than accumulating unsupported post-hoc assertions.

**Why:** The only way Verus can use a break condition after the loop is if it was captured in state that is part of the loop invariant. Ghost state is not compiled, so capturing it changes only verification instrumentation. Biconditional invariants ensure the early-exit scenario has direct proof support.

**Check:** After the loop, the desired fact follows from the invariant plus the loop exit condition alone; there are no proof-mode executable calls, and the invariant is maintained both when the break branch is taken and when normal iterations leave the ghost state unchanged.

**Avoid or stop:**
- Unverified break-capture remedies from failed logs are recovery guidance, not verifier-confirmed success; test the exact invariant before relying on it.
- Do not set a ghost break flag in only the break branch and forget to constrain it in the invariant, because normal iterations will fail to maintain the relation.
- Do not try to prove break provenance by re-executing executable operations after the loop; Verus separates proof and exec modes.
- Do not keep patching assertions around an under-specified loop if the control flow itself prevents a stable invariant; restructure the loop.

<a id="verus-global-043"></a>

## verus_global_043 — Prioritize a loop invariant that directly implies the primary postcondition over auxiliary fixes

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A loop is written or being patched, but the main postcondition remains unproven after the loop, while work drifts toward body assertions, helper lemmas, arithmetic bounds, or validity side facts.

**Obstacle:** The loop invariant is not strong enough to imply the target postcondition. Additional assertions or auxiliary lemmas may prove local side conditions but do not bridge the main postcondition, so the proof remains stuck.

**Mechanism:** Redirect proof effort to the loop invariant that is most aligned with the postcondition. It should be updated so that, together with the final loop exit condition, it directly entails the top-level obligation. Keep the loop body simple enough that the invariant is re-established automatically, and reserve auxiliary lemmas for after the central bridge is in place.

**Procedure:**
1. Identify the exact fact required by the failing post-loop proof, such as an element property at the current cursor, an early-exit property, or a full-range quantifier.
2. Write or strengthen the loop invariant in the shape of that fact over the processed prefix or exit scenario so the final loop state implies the postcondition.
3. Remove or defer in-body assertions and peripheral lemma work unless they are needed to prove the chosen invariant; prefer strong invariants over multiple local assert statements.
4. After the main postcondition follows from the invariant, return to auxiliary validity or bounds lemmas only if they are still required.

**Why:** Verus uses loop invariants as the only facts available after the loop. If the invariant does not imply the main postcondition, no amount of auxiliary arithmetic or local body assertions will close the top-level gap. Focusing on the central implication reduces wasted iterations.

**Check:** The post-loop proof obligation is discharged by the invariant plus the loop exit condition without a chain of auxiliary lemmas or body assertions; local interventions should be absent or obviously subsumed by the invariant.

**Avoid or stop:**
- Do not confuse this with a license to drop necessary bounds invariants; the core invariant still must be maintainable.
- Auxiliary lemmas are not harmful per se, but they are secondary if the main postcondition is still open.
- Avoid treating this as a generic 'write better invariants' slogan; apply it only when the main postcondition is the failing obligation.

<a id="verus-global-044"></a>

## verus_global_044 — Add a nonnegative bound-minus-counter decreases measure to while loops

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Verus while loops with a monotonic counter moving toward a known upper or lower bound when the verifier reports a missing decreases clause or termination failure. For the upper-bound form, includes inclusive upper-bound loops with condition `counter <= upper_bound` where the invariant allows the counter to reach `upper_bound + 1` before/at exit, making a naive `upper_bound - counter` measure negative.

**Obstacle:** Verus rejects a while loop or reports a termination error because the loop must have a decreases clause and an invariant. A counter moving toward a bound has no explicit well-founded measure. In inclusive upper-bound loops, `upper_bound - counter` can drop below zero when the counter reaches `upper_bound + 1`, violating Verus's requirement that decreases measures remain non-negative.

**Mechanism:** An explicit `decreases <bound> - <counter>` expression gives Verus a non-negative measure that strictly decreases on each iteration while the loop remains in range. For inclusive upper-bound loops where the condition is `counter <= upper_bound` and the invariant permits the counter to reach `upper_bound + 1`, use `decreases upper_bound + 1 - counter` instead so the measure stays non-negative at the final allowable counter value.

**Procedure:**
1. Inspect the loop header and invariant to identify the monotonic counter and its terminal bound, and determine whether the loop condition or invariant allows the counter to reach one above an inclusive upper bound.
2. If `bound - counter` remains non-negative throughout the states allowed by the invariant, add `decreases bound - counter`.
3. If the loop uses an inclusive upper-bound condition such as `counter <= upper_bound` and the invariant permits `upper_bound + 1`, avoid `decreases upper_bound - counter`; add `decreases upper_bound + 1 - counter` instead.
4. Keep the required loop invariant in place; do not omit or alter it merely to make a decreases measure pass.
5. Re-run Verus and confirm the termination check accepts the loop.

**Why:** Verus requires while loops to have both an invariant and a decreases expression. A bound-minus-counter expression is strictly decreasing and non-negative while the loop is in range. For inclusive upper-bound loops that allow the counter to reach `upper_bound + 1`, the measure must be shifted by one to remain non-negative at the final allowable counter value.

**Check:** Each loop has a decreases expression that is non-negative at every state satisfying the invariant and strictly decreases with each iteration. For inclusive-bound loops, verify that the shifted measure remains non-negative at the final allowable counter value.

**Avoid or stop:**
- Do not use a measure that can become negative under the loop invariant.
- Do not treat a decreases clause as a substitute for required loop invariants.
- Do not use the shifted `upper_bound + 1 - counter` measure for strict upper-bound loops where the simpler `upper_bound - counter` measure is already valid.
- Do not alter the invariant only to make a bad measure pass; choose the measure to match the actual loop invariant.

<a id="verus-global-045"></a>

## verus_global_045 — Use an explicit sequence-length decreases clause for recursive proof functions and lemmas

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Recursive Verus proof functions or lemmas that induct over a sequence or make a recursive call on a shorter sequence, and produce a cannot-prove-termination or must-have-a-decreases error.

**Obstacle:** Verus rejects recursive proof functions or lemmas without an explicit decreases clause, even when the recursion appears structurally decreasing by sequence length.

**Mechanism:** Add a `decreases` clause whose measure is the length of the sequence argument being reduced, such as `decreases seq.len()`. The recursive call must be on a strictly shorter sequence.

**Procedure:**
1. Identify the sequence argument that shrinks in every recursive call.
2. Add `decreases seq.len()` after the requires/ensures lines and before the function body.
3. Ensure each recursive call is on a sequence whose length is strictly smaller than the current sequence length.
4. Re-run Verus to confirm the termination check passes.

**Why:** Verus checks recursive proof functions by well-founded decreases expressions. Sequence length is a natural well-founded measure when the recursive argument is structurally shorter.

**Check:** The recursive proof function has an explicit sequence-length decreases clause, and every recursive call uses a strictly shorter sequence argument.

**Avoid or stop:**
- Do not add a sequence-length measure if recursion is not on a smaller sequence or if another data-structure measure is needed.
- Do not confuse sequence recursion with finite-set recursion; use the relevant measure for the data structure.

<a id="verus-global-046"></a>

## verus_global_046 — Induct over finite sets using decreases set length and element removal

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Recursive proof functions or lemmas over finite sets that require induction on set size, or where Verus reports termination failure and the induction step needs a smaller set.

**Obstacle:** A recursive proof over a finite set has no evident termination measure, and the induction step needs a strictly smaller set to unfold recursive definitions.

**Mechanism:** Add `decreases s.len()` to the proof function. Split cases into empty and non-empty sets, choose an arbitrary element from the non-empty set, apply the induction hypothesis to the smaller set after removing that element, and then reinsert/aggregate the element with the relevant operation.

**Procedure:**
1. Add `decreases s.len()` to the recursive proof function or lemma over the finite set.
2. Handle the empty set as the base case.
3. For a non-empty set, choose an arbitrary element from the set.
4. Unfold the recursive definition or operation as the result for the chosen element combined with the result for the set without that element.
5. Apply the induction hypothesis to the smaller set after removal.
6. Combine the result with insert/fold/map properties to reestablish the property for the original set.

**Why:** Set-size reduction is a well-founded measure for finite sets. Removing an element provides a strictly smaller set for the induction hypothesis and mirrors recursive set definitions.

**Check:** The proof has a decreases clause using set length, and the non-empty case applies induction to a set whose length is strictly smaller after one element is removed.

**Avoid or stop:**
- Do not apply this pattern to sequence induction unless the structure is actually a finite set with removal.
- Do not forget to reinsert or aggregate the chosen element; induction only on the smaller set leaves an open goal.

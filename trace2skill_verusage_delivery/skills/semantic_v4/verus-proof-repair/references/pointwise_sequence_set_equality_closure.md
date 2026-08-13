# Pointwise, Universal, and Extensional Sequence/Set Closure

**Consult when:** A universal ensures, set/sequence equality, singleton contents, elementwise lemma application, or post-loop full-range equality must be closed by explicit forall/pointwise reasoning and extensionality.

**Do not consult when:** The missing fact is a trigger selection issue, a recursive fold recurrence, or a branch/return postcondition with no elementwise equality.

<a id="verus-global-023"></a>

## verus_global_023 — Discharge universal ensures and arbitrary-value postconditions with `assert forall`

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** `ensures forall|x: T| P(x)` or a postcondition involving an underspecified returned value whose concrete identity is unavailable in the ensures.

**Obstacle:** The verifier does not close a universal postcondition from pointwise facts, per-instance lemmas, or an underspecified runtime value by itself.

**Mechanism:** Make the universal goal explicit with `assert forall`; prove the body for an arbitrary element, wrap a pointwise lemma call inside the `by` block, or instantiate the asserted forall with the returned concrete value.

**Procedure:**
1. Restate or strengthen the target postcondition as `forall|x: T| P(x)` when the concrete witness is unavailable or when a forall ensures must be closed.
2. Inside the proof, write `assert forall|x: T| P(x) by { ... }` and prove `P(x)` for a fresh, arbitrary `x`.
3. If the body already follows from a pointwise lemma, call that lemma for the arbitrary or concrete instance inside the `by` block.
4. When the witness is an underspecified returned value, assert the forall and then assert the same predicate with the returned concrete value to instantiate it.
5. Let the asserted forall or instantiation close the enclosing ensures without adding trigger annotations.

**Why:** Merges four records that share the same observable trigger, a universal ensures or arbitrary underspecified value, and the same missing bridge: Verus needs an explicit `assert forall` to connect pointwise or per-instance reasoning to the quantified postcondition. The variants are compatible stages in the same closure procedure.

**Check:** The proof function verifies after the `assert forall` and any concrete instantiation assertion close the stated ensures.

**Avoid or stop:**
- Do not use for quantifier trigger selection or missing-trigger warning repairs.
- Do not use to discharge universal postconditions that require recursive or fold recurrence lemmas; this pattern assumes the body is already provable pointwise or via a direct lemma.
- Do not present an unverified remedy from a failed trajectory as verifier-confirmed success.

<a id="verus-global-024"></a>

## verus_global_024 — Set equality by explicit membership forall and extensionality

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Set equality goal `A == B` where both sides are sets or sequence-derived sets and membership can be stated with `contains`.

**Obstacle:** Verus will not close set equality from set internals or a bare equality assertion; it needs the extensional membership equivalence or mutual inclusion to be explicit.

**Mechanism:** Assert `forall|y| A.contains(y) == B.contains(y)` or prove both subset directions explicitly, then close with set extensionality `A =~= B` or an equality assertion.

**Procedure:**
1. Identify the two set operands in the equality goal.
2. Write `assert forall|y| left_set.contains(y) == right_set.contains(y) by { ... }` or split into two `assert forall` directions for `==>`.
3. Inside the body, prove containment by membership or case analysis; for singleton sequence-derived sets, assert the singleton sequence length and first-element facts if needed.
4. After the forall membership equivalence is established, assert extensional equality `left_set =~= right_set` or `assert(left_set == right_set)` to close the goal.

**Why:** Merges three records with the same trigger—set equality—and the same mechanism—explicit forall membership plus extensionality. The differences among bidirectional equivalence, mutual subset assertions, and singleton case analysis are compatible surface variants.

**Check:** The set equality goal verifies after the explicit forall membership assertion and the closing `=~=`/equality assertion.

**Avoid or stop:**
- Do not use for recursive or fold-derived set equalities that first require recurrence lemmas.
- Do not use for set membership or cardinality via insert/fold/witness case splits unless the witness extraction is represented separately.
- Do not rely on this to fix trigger warnings; triggers are outside the mechanism.

<a id="verus-global-025"></a>

## verus_global_025 — Ground singleton sequence contents by index and length facts

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Reasoning about a singleton sequence `seq![x]` or a sequence known to have one element, especially when connecting `to_set()` and singleton set membership.

**Obstacle:** Verus does not automatically connect the singleton sequence's length and sole index to the expected element during quantified membership or equality reasoning.

**Mechanism:** Inside the relevant forall or membership body, explicitly assert `seq.len() == 1` and `seq[0] == element`; this grounds the sequence shape for the verifier.

**Procedure:**
1. Identify the singleton sequence and expected element in the quantified body.
2. Assert `seq.len() == 1` to expose the only valid index.
3. Assert `seq[0] == element` to connect the sole position to the explicit value.
4. Use these facts to close the immediate membership or set-element claim; if the larger goal is set equality, continue with extensionality.

**Why:** Kept as a singleton because it is a lower-level grounding primitive that appears inside larger singleton-set equality proofs but is independently reusable.

**Check:** The singleton membership or element claim verifies after both the length fact and the first-index equality fact are explicit.

**Avoid or stop:**
- Do not use for general set/cardinality via insert/fold/witness splits.
- Do not use as a replacement for set extensionality; it only supplies singleton sequence facts.

<a id="verus-global-026"></a>

## verus_global_026 — Elementwise lemma application for collection-level predicates

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Collection-level property over sequences or views where the element type exposes a lemma that proves the needed per-element fact.

**Obstacle:** Verus does not automatically propagate a collection-level relation to each element or invoke the element-type lemma for each pair.

**Mechanism:** Inside an index-bounded `assert forall`, guard the index range and call the element-type lemma on the corresponding elements, then use the per-element conclusions for the collection-level goal.

**Procedure:**
1. Establish equality of lengths or index ranges between the two collections if required.
2. Write `assert forall|i| 0 <= i < binding_range ==> collection_predicate_at(i) by { ... }`.
3. Inside the `by` block, apply the element-type lemma to the pair or element at index `i`.
4. Use the resulting per-element equivalence or property to close the body.
5. Let the established forall provide the collection-level pre/postcondition fact.

**Why:** Merges two records with the same index-guarded element lemma application mechanism; one proves symmetry and one proves marshalability equivalence, but the proof shape is identical.

**Check:** The collection-level predicate verifies after the element-type lemma is called for each guarded index inside the `assert forall`.

**Avoid or stop:**
- Do not use when the element property itself requires recursive or fold recurrence lemmas; this skill assumes a direct element-type lemma already exists.
- Do not skip the index bounds guard; verifier bounds-check warnings may otherwise block the proof.

<a id="verus-global-027"></a>

## verus_global_027 — Post-loop universal and sequence-equality closure from loop invariants

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A loop invariant already maintains a per-index, pairwise, or elementwise property, but the postcondition requires the same property for all indices after the loop, possibly as sequence or set extensional equality; in the sequence-equality variant, two sequences have equal length and the loop invariant maintains equality for every index up to a counter that ends at that length.

**Obstacle:** Verus does not automatically lift the loop invariant to a full-range universal statement or to `=~=` after the loop exits: the SMT solver sees the per-index or elementwise invariant and exit/length facts, but does not convert them into the required full-range postcondition or sequence equality.

**Mechanism:** After the loop exits, close the full-range goal explicitly. For universal properties, write `assert forall|j| <range_condition> ==> <predicate> by { ... }` and instantiate the loop invariant at `j` using the exhaustion bound to discharge the range guard. For sequence or set equality, either assert the pointwise equality for all valid indices and then assert the extensional equality `source =~= target`, or call a previously proven helper lemma that lifts elementwise equality plus equal lengths to full sequence equality in a proof block immediately before return.

**Procedure:**
1. Ensure the loop invariant records the required per-index, pairwise, or elementwise fact, and that the loop counter has reached the exhaustion bound; if the postcondition is an extensional sequence or set equality, also maintain or derive length equality.
2. After the loop, establish the exit and length facts that will be used as guards for the whole-range conclusion, such as the counter equals the bound and the sequence lengths are equal.
3. If closing a universal property directly, write `assert forall|j| <range_condition> ==> <predicate> by { ... }` for the whole range. Inside the `by` block, assert the loop invariant at the relevant index `j` or adjacent indices and perform the simple arithmetic showing the range condition is covered.
4. If closing sequence or set equality, either assert pointwise equality for all valid indices and then assert the extensional equality `source =~= target`, or obtain/prove a helper lemma lifting pointwise equality and equal lengths to full sequence equality and call it in a proof block immediately before return.
5. Use the established full-range assertion or equality to close the enclosing postcondition; do not rely on the solver to infer it from the loop invariant alone.

**Why:** Merges two compatible variants of the same post-loop closure mechanism: one uses explicit post-loop `assert forall` and extensional equality, and the other uses a helper lemma. Both solve the same obstacle by instantiating or lifting the loop invariant after exhaustion, without weakening the procedure.

**Check:** The post-loop `assert forall` body, the `source =~= target` assertion, or the helper-lemma call verifies from the loop invariant, exhaustion bound, and length-equality facts; the original postcondition closes.

**Avoid or stop:**
- Do not use if the loop invariant is missing or too weak; strengthen the invariant first.
- Do not use for pre-loop universal goals or for deriving the underlying elementwise fact via recursion or fold lemmas.
- Do not use if the sequences or sets have different lengths or the invariant covers only part of the required range.
- Do not omit the length-equality fact required by extensional equality or by the lifting lemma.

<a id="verus-global-028"></a>

## verus_global_028 — Sequence equality by length, pointwise equality, and `=~=`

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Direct sequence equality `seq1 == seq2` for any sequence operations, where length equality and pointwise element equality can be asserted.

**Obstacle:** Verus does not close sequence equality from a bare equality assertion or from structural reasoning alone.

**Mechanism:** Assert equal lengths and a forall over valid indices showing matching elements, then use built-in extensionality `seq1 =~= seq2` to conclude equality.

**Procedure:**
1. Assert the two sequences have equal lengths.
2. Write `assert forall|i| 0 <= i < length ==> seq1[i] == seq2[i] by { ... }` to establish pointwise equality.
3. After the pointwise forall, assert `seq1 =~= seq2`.
4. Use the extensionality assertion to close the sequence equality goal.

**Why:** Kept as a singleton because direct non-loop sequence extensionality is a distinct basic mechanism; loop-derived variants are consolidated in the post-loop closure skill.

**Check:** The sequence equality goal verifies after equal lengths, pointwise equalities, and `=~=` are asserted.

**Avoid or stop:**
- Do not use for loop-derived equality where the pointwise facts require post-loop invariant instantiation; combine with that skill instead.
- Do not use if the sequence elements require fold or recursive lemmas unrelated to index extensionality.

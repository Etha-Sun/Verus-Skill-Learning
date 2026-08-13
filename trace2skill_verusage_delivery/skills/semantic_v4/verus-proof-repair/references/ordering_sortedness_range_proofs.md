# Ordering, Sortedness, Gap, and Range-Bound Proofs

**Consult when:** The stuck goal depends on custom comparator order properties, trichotomy/gap case splits, inclusive/exclusive range mismatches, consecutive sorted-key gaps, contiguous sorted-range induction, sortedness after one update/insertion, or transitive index-bound chains.

**Do not consult when:** The obstacle is only a pointwise/set extensionality or trigger problem, or the ordering facts are already sufficient and the remaining gap is loop/invariant or serialization-related.

<a id="verus-global-001"></a>

## verus_global_001 — Unlock user-defined comparator transitivity and trichotomy before ordered reasoning

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A proof goal depends on a user-defined comparison relation or custom comparator and requires chaining strict inequalities or trichotomy, but the SMT solver cannot derive the order properties of that relation.

**Obstacle:** Transitivity and trichotomy facts for the custom comparison relation are packaged behind a comparison-properties lemma, so the SMT context lacks the axioms needed to connect comparison assertions to actual comparison results.

**Mechanism:** Expose the custom order axioms to the SMT context by invoking the comparison type's properties lemma at the beginning of the proof function or proof block, rather than asserting individual transitive consequences by hand.

**Procedure:**
1. Identify whether the ordering relation is defined through a custom comparison function or specification rather than built-in integer order.
2. At the beginning of the proof function, lemma, or proof block, call the comparison-properties lemma for the key/comparison type.
3. Let the exposed transitivity and trichotomy axioms make subsequent chain comparisons and order deductions available to the solver.
4. For sortedness preservation after an update, invoke or re-invoke the comparison properties before proving the sortedness assertion.

**Why:** The custom comparison's transitivity and trichotomy axioms are available only after the properties lemma is brought into the proof context; once exposed, the SMT solver can connect ordering assertions to the actual comparison results without additional manual transitivity lemmas.

**Check:** After invoking the properties lemma, ordering chain assertions that previously failed should close without manual transitivity or trichotomy proofs.

**Avoid or stop:**
- Do not use this as a substitute for explicit case splits when the goal requires a witness or a no-intermediate-key gap proof.
- Do not invoke unrelated order properties when the comparator is not the source of the missing order facts.

<a id="verus-global-002"></a>

## verus_global_002 — Trichotomy-driven case split for gap and adjacent order facts

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A goal must prove an ordering relation or gap for an arbitrary intermediate key between two bounds, and the relation has disjoint alternatives beyond strict less-than, including equality and possibly an iterator-end sentinel.

**Obstacle:** The solver does not automatically partition the intermediate key into the disjoint ordering alternatives needed to apply existing gap or boundary lemmas; missing equality or sentinel cases are especially likely to block the proof.

**Mechanism:** Define or use an exhaustive trichotomy lemma for the ordering relation, including sentinel or end-of-iteration cases where relevant, then split the intermediate key on a pivot predicate and dispatch each case to transitivity, a gap lemma, equality substitution, or sentinel reasoning.

**Procedure:**
1. For a custom iterator or key order, first define a trichotomy lemma enumerating less-than, greater-than, equality, and any end-of-iteration sentinel case.
2. For a no-intermediate-key goal between outer bounds, split the arbitrary key by a pivot comparison such as whether the key is below the pivot.
3. In the less-than branch, chain transitivity from the key through the pivot to the outer bound and apply the corresponding gap lemma.
4. In the non-less-than branch, invoke trichotomy to obtain either pivot less than key, equality, or sentinel; use the pivot-side gap or equality substitution to derive the required outer-bound relation.
5. Avoid reasoning about overlapping order relationships without first exhausting the partition.

**Why:** An ordered proof becomes mechanical when the possible positions of the intermediate key are explicitly enumerated, so each sub-case maps directly to an existing gap or a transitive chain instead of requiring simultaneous relational reasoning.

**Check:** Every intermediate key case has been matched to a gap lemma, a transitive chain, or an equality or sentinel contradiction, leaving no unhandled ordering possibility.

**Avoid or stop:**
- Do not introduce a large trichotomy lemma if the relevant case split has only a binary condition and sentinel handling is not needed.
- Do not use a pivot split that is not implied by the available order facts or gaps.

<a id="verus-global-003"></a>

## verus_global_003 — Resolve inclusive/exclusive range mismatches by inspecting predicate definitions

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** The goal appears to require a property over an inclusive index or key range while an existing lemma covers an adjacent or exclusive range, creating an apparent off-by-one or boundary mismatch.

**Obstacle:** Naive arithmetic manipulation of bounds treats the upper bound as inclusive and creates a spurious obligation for the right endpoint, even though the target predicate's range semantics may exclude it.

**Mechanism:** Read the actual definition of the range predicate or iterator relation used by the goal; if it is exclusive on the upper bound or otherwise matches an existing lemma's syntactic range, use that lemma directly instead of proving unnecessary boundary cases.

**Procedure:**
1. Before doing bound arithmetic, inspect the definition of the target range predicate, especially whether the upper bound is treated exclusively.
2. Compare the goal's syntactic range with the ranges of existing lemmas that consume the same predicate.
3. If the goal's apparently inclusive boundary is not actually generated by the exclusive predicate, use the existing lemma directly.
4. Do not add an extra proof branch for a boundary element the predicate never includes.

**Why:** Specification predicates often define intervals with exclusive upper bounds, so an invariant over an inclusive index precondition still only generates keys inside the lemma's exclusive key range; boundary mismatches disappear after aligning the semantics.

**Check:** The proof reduces to a single lemma call or direct assertion with no separate handling of the upper-bound element.

**Avoid or stop:**
- Do not assume exclusive semantics without reading the actual predicate definition; if the upper bound is inclusive, use an appropriate bridge lemma or case split.
- Do not apply adjacent-range lemmas when the predicates differ syntactically or semantically.

<a id="verus-global-004"></a>

## verus_global_004 — Prove consecutive sorted-key gaps via sorted-index order contradiction

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A proof must establish that there is no key belonging to a strictly sorted finite key sequence strictly between two consecutive elements at indices i and i+1.

**Obstacle:** The SMT solver can use sortedness to compare values, but it does not automatically connect a key's value being between those at two indices to an impossible index range between consecutive indices.

**Mechanism:** Prove an order-preserving index lemma: if a key in a strictly sorted sequence lies strictly between the values at two indices, then its index lies strictly between those indices. For consecutive indices, no integer lies strictly between them, producing a contradiction that proves the gap.

**Procedure:**
1. State a sorted-index order lemma: for a sorted sequence, if the value at one index is less than a key and that key is less than the value at another index, and the key appears at some index, then the key's index is strictly between those two indices.
2. Prove this lemma from strict sortedness and the order-preserving property of indices.
3. For consecutive indices, instantiate the lemma and observe that no integer can lie strictly between them.
4. Use the resulting contradiction to prove the consecutive-key gap lemma: the open interval between the two consecutive values contains no key from the same sequence.

**Why:** The index-order lemma converts value ordering into integer index ordering; the consecutive case immediately becomes an impossible integer inequality, which is easier for the solver to close than a nested quantifier over values.

**Check:** The proof explicitly shows the contradiction in the index ordering, and the final gap obligation is discharged by integer arithmetic after instantiation.

**Avoid or stop:**
- Do not apply this to non-strictly-sorted sequences unless the index-order lemma is adapted to handle duplicates.
- Do not use this as a replacement for a more general GLB-based gap if the validity condition requires it.

<a id="verus-global-005"></a>

## verus_global_005 — Inductively decompose contiguous sorted-key range proofs

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A uniform property must be proved over a contiguous range of sorted keys, and a direct monolithic proof does not close or is too complex.

**Obstacle:** The solver does not automatically exploit the recursive structure of the range; a direct proof over the whole interval leaves too many cases and does not leverage existing range-extension lemmas.

**Mechanism:** Split the interval into subranges, prove the property recursively or inductively for those subranges, then use an available extension lemma to combine the subrange results into the whole range.

**Procedure:**
1. Choose an interval decomposition that matches the available extension lemma, often splitting off one endpoint as a midpoint.
2. Prove the property for the left and right subranges, using induction on range length when necessary.
3. Apply the existing range-extension or combination lemma to the two subrange results.
4. Prefer this recursive decomposition over an unstructured direct proof if range-extension lemmas already exist.

**Why:** Range predicates and lemmas are often built inductively, so a goal over a larger range can be closed by aligning with that inductive structure instead of re-justifying every key from scratch.

**Check:** The proof has explicit subrange obligations and a final extension-lemma call; there is no remaining monolithic range goal.

**Avoid or stop:**
- Do not decompose if the target range is not contiguous or if the available extension lemma requires additional disjointness or ordering preconditions.
- Do not over-decompose when a direct adjacent-range lemma call suffices.

<a id="verus-global-006"></a>

## verus_global_006 — Prove sortedness after a single key update by index-case split

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A sorted sequence has one element updated or replaced, and the goal is to re-establish sortedness for all pairs of indices.

**Obstacle:** The universal sortedness assertion over all pairs is not automatically reducible to the pre-update and post-update facts; the solver must be shown cases relative to the updated index.

**Mechanism:** Assert the full sortedness condition over all index pairs, then split into cases where the lower index equals the updated index, the upper index equals the updated index, or neither equals the updated index. Use new placement facts for the updated index and old sortedness for unchanged pairs.

**Procedure:**
1. After the update, assert the full sortedness condition over all index pairs.
2. Split the proof by whether the lower index equals the updated index, the upper index equals it, or neither equals it.
3. In the case where the lower index is the updated index, use the fact that the new value is less than its immediate successor from placement or prelude facts.
4. In the case where the upper index is the updated index, use the fact that the immediate predecessor is less than the new value.
5. In the neither case, rely on the old sortedness fact because the pair is unchanged.

**Why:** A single update only challenges sortedness for pairs involving the updated index; a case split mirrors the geometric placement constraints and permits each case to be discharged by local facts.

**Check:** The proof explicitly handles all three cases relative to the updated index and does not attempt to re-prove sortedness for unchanged pairs.

**Avoid or stop:**
- Do not use when the update can change many elements or when the sequence is not sorted before the update.
- Do not ignore degenerate cases at the start or end of the sequence; ensure the asserted facts cover them or add boundary cases.

<a id="verus-global-007"></a>

## verus_global_007 — Re-establish map-wide invariant after a single key insertion by old/new key split

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A map is mutated by inserting one key, and the goal is a map-domain invariant over every key in the domain.

**Obstacle:** The solver cannot automatically distinguish the newly inserted key from keys already present, so it does not combine the old invariant and the new-key fact.

**Mechanism:** Assert the map-wide invariant as a forall over the domain after insertion, then split the domain into the newly inserted key and all pre-existing keys; use the old invariant for existing keys and the inserted-key precondition for the new key.

**Procedure:**
1. State the map-wide invariant as an assert-forall over the domain after insertion.
2. In the proof block, identify the newly inserted key from the insertion call and the precondition or fact that covers it.
3. For the newly inserted key, use the explicit new-key property given by the precondition.
4. For every other key, use the fact that the map before insertion already satisfied the invariant.
5. Let the SMT solver case-split on whether the quantified key equals the inserted key inside the forall proof.

**Why:** A single insertion changes the domain by adding one key, so the old invariant is already enough for all unchanged keys; the proof only needs to combine the old invariant on existing keys with the per-key fact for the new key.

**Check:** The forall assertion is closed without additional lemmas, and the proof explicitly cites both the old invariant and the new-key fact.

**Avoid or stop:**
- Do not use if the insertion can alter values for existing keys or if the invariant depends on cross-key relationships beyond per-key properties.
- Do not ignore the possibility that the inserted key is already present if the map update semantics allow it.

<a id="verus-global-008"></a>

## verus_global_008 — Encode transitive index-bound chains as one invariant

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A proof relies on separate ordering facts of the form A <= B and B <= C, and a subsequent derived arithmetic or index comparison only follows when the chain is available as a compact transitive fact.

**Obstacle:** Separate loop invariants or assertions give the solver A <= B and B <= C, but it does not always combine them in the context where a derived bound such as a lower cursor plus deletion count is less than the original size is needed.

**Mechanism:** Write the combined chain invariant directly as A <= B <= C rather than as two separate inequalities, making the transitivity fact immediately available to the solver.

**Procedure:**
1. Identify index parameters bounded by a loop or insertion bound and by a lower-to-upper relation.
2. Combine the adjacent inequalities into a single chained assertion or invariant, such as lower <= cursor <= original_length.
3. When a later goal needs a derived bound from a difference relation, the chain supplies the needed bridge from the cursor to the original length without manual transitivity.
4. Keep the chained invariant in the loop or proof context where the derived bound is required.

**Why:** SMT solvers often use chained arithmetic atoms more effectively than separate linear inequalities; the chain directly connects the offset bound to the original size bound and exposes the transitive relationship.

**Check:** The derived bound is discharged once the chain invariant is present, without an explicit transitivity lemma call.

**Avoid or stop:**
- Do not combine unrelated inequalities into one chain if the middle term is not the same.
- Do not use a chain when one inequality has side conditions that need to be preserved separately.

<a id="verus-global-009"></a>

## verus_global_009 — Recover GLB index ordering proof from failed unsupported assertions

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A proof requires ordering between greatest-lower-bound indices derived from GLB specifications and sortedness, after prior attempts with assert-false or unfinished contradictions failed.

**Obstacle:** The solver cannot close the index ordering from high-level GLB and sortedness facts alone; previous attempts left assertions unsupported or used assumptions instead of explicit instantiations.

**Mechanism:** Convert the ordering into an explicit contradiction argument: assume the opposite index order, derive an order relation on the corresponding keys from sortedness, then instantiate the greatest conjunct of the GLB specification with the lower-bound key as a witness.

**Procedure:**
1. Do not rely on assert-false or unresolved comments, and do not leave an unproven assumption in the proof.
2. Assume the negated index order, for example that the lower GLB index is greater than the upper GLB index.
3. Use sortedness of the key sequence to derive that the key at the lower GLB index is greater than the key at the upper GLB index.
4. Instantiate the greatest-lower-bound specification's greatest conjunct with the lower GLB key as a witness.
5. Derive a contradiction with the known lower-bound relation to the upper endpoint.

**Why:** The contradiction becomes provable only when the GLB specification is instantiated with a concrete witness, making the greatest-lower-bound fact applicable to the key ordering produced by negating the index order.

**Check:** The proof contains an explicit witness for the GLB specification and a derived contradiction; there are no assert-false placeholders or assumptions.

**Avoid or stop:**
- This recovery route is untested and should not be presented as a verified success; validate it with the verifier before depending on it.
- Do not use unsupported assertions or assume statements as placeholders in an attempted proof.
- Do not instantiate the GLB specification with the wrong witness or omit sortedness context.

<a id="verus-global-010"></a>

## verus_global_010 — Bridge range-consistency statements with explicit witnesses instead of bare forall

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A goal needs to show one range-consistency predicate over a wider key interval implies another, and previous attempts used assert-forall with high-level comments or simple references to gap and GLB lemmas without instantiating them.

**Obstacle:** The SMT solver does not automatically instantiate nested domain quantifiers in the range-consistency or validity specifications; asserted forall blocks that only restate the goal or mention the gap property without concrete witnesses fail to close.

**Mechanism:** For each key in the wider interval, identify a witness satisfying the lower-bound range or GLB conditions, prove that witness is valid, and instantiate the gap or validity clause explicitly so the target equality is derived stepwise.

**Procedure:**
1. Do not use bare assert-forall blocks whose proof body contains only comments or a restatement of the goal.
2. For each key between the original iterators, locate the greatest lower-bound key from the lower-bound set or key list that is less than or equal to the key.
3. Prove that this witness lies within the GLB range and satisfies the preconditions of the validity or gap lemma.
4. Instantiate the range-consistency or validity gap clause with that witness to conclude the value equality for the key.
5. If the bridge requires ordering between GLB indices, prove that ordering separately before invoking range-consistency lemmas.

**Why:** Nested quantifiers in complex validity specifications require explicit witness terms; the solver can then perform the proof for each witness instead of searching for instantiation triggers across multiple specifications.

**Check:** Every domain key has an explicit witness and an instantiated gap or validity clause; no assertion remains as a high-level comment or unresolved forall over the whole range.

**Avoid or stop:**
- This is a recovery pattern from a failed trajectory; it is untested and not verifier-confirmed success.
- Do not rely on SMT alone for quantifier instantiation when the specification contains nested or triggered quantifiers.
- Do not confuse GLB-range lemmas with the original range without proving the GLB indices or witness ordering.

# Finite-Set Cardinality, Membership, and Equality Proofs

**Consult when:** The goal is set cardinality/finiteness, set equality or subset membership, sequence-to-set length, choose-based witness extraction, derived set operations, or membership transfer through sequence transformations.

**Do not consult when:** The goal is an ordering chain, loop invariant, or serialization segment, even if it mentions sequences; use those references instead.

<a id="verus-global-011"></a>

## verus_global_011 — Duplicate-free sequence-to-set cardinality by insert-length axiom

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** When proving `s.to_set().len() == s.len()` for a duplicate-free sequence `s`, or deriving cardinality changes after inserting a fresh element into a set.

**Obstacle:** The solver does not automatically connect insertion to cardinality or sequence-to-set conversion to length; the proof needs an explicit library axiom and induction.

**Mechanism:** Use `vstd::set::axiom_set_insert_len` after establishing freshness; for sequence-to-set conversion, decompose the sequence into first/rest, apply induction, show the set equals `rest.to_set().insert(first)`, and then connect lengths.

**Procedure:**
1. Prove or assert `!s.contains(e)` for the inserted element `e`, or `!s.to_set().contains(e)`.
2. Call `vstd::set::axiom_set_insert_len::<T>(s, e)` to obtain `s.insert(e).len() == s.len() + 1`.
3. For sequence-to-set length, split the sequence into `first` and `rest`, and preserve the no-duplicates property on `rest`.
4. Apply the induction hypothesis to `rest`, then prove that `first` is not in `rest.to_set()`.
5. Derive `s.to_set() == rest.to_set().insert(first)` by extensionality and combine lengths with the insert-length axiom.

**Why:** The source cards succeed by linking the missing cardinality fact to a library axiom and by making the sequence-to-set equality extensional before applying length reasoning, which is the bridge Verus needs.

**Check:** Confirm the inserted element is not already present before invoking the axiom; confirm the sequence is duplicate-free in the inductive step.

**Avoid or stop:**
- Do not use when the element may already be in the set, because the insert length is not `+1` and the axiom precondition fails.
- Do not use for sequences with duplicates unless the lemma is generalized accordingly.

<a id="verus-global-012"></a>

## verus_global_012 — Use fold-representation lemmas to prove derived set-operation finiteness

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Proving finiteness of a high-level set operation such as `s.map(f)` when only lemmas about `map_fold` are available and the proof body is empty.

**Obstacle:** The high-level operation has no direct finiteness lemma; the solver cannot lift facts from the recursive definition.

**Mechanism:** Invoke external-body lemmas that provide finiteness of the fold and equality between the fold and the high-level operation, then chain the conclusions.

**Procedure:**
1. Inspect available lemmas such as `map_fold_finite` and `map_fold_ok`.
2. Assert or call `map_fold_finite` to obtain finiteness of the intermediate `map_fold` result.
3. Assert or call `map_fold_ok` to equate the intermediate result with the high-level operation such as `s.map(f)`.
4. Conclude the required property, for example `s.map(f).finite()`, from the chained lemma conclusions.

**Why:** The successful trajectory shows the postcondition is proved immediately by chaining two existing lemmas rather than re-proving folding behavior.

**Check:** Verify the fold lemmas are in scope and their preconditions are satisfied by the current proof state.

**Avoid or stop:**
- Do not call the lemmas before establishing their preconditions.
- Do not treat this as a proof of the fold lemmas themselves.

<a id="verus-global-013"></a>

## verus_global_013 — Preserve finiteness through insert in recursive set-fold proofs

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Proving `map_fold(s, f).finite()` by induction on a recursive set fold whose step inserts into a known-finite set.

**Obstacle:** The induction hypothesis establishes finiteness of a smaller set, but the solver does not automatically see that insert preserves finiteness.

**Mechanism:** Explicitly assert finiteness preservation across the insert step, strengthening the induction step.

**Procedure:**
1. Obtain or assert the induction hypothesis for the smaller set, for example `map_fold(s.remove(x), f).finite()`.
2. Assert that `insert` preserves finiteness for the constructed set.
3. Use that preservation fact to prove the recursive composite `map_fold(s, f).finite()`.

**Why:** The successful proof closes by combining the inductive hypothesis with an explicit preservation assertion, avoiding manual reasoning about set sizes in the final derivation.

**Check:** Ensure the recursive argument is actually a smaller set and the insert preserves the finiteness property being proved.

**Avoid or stop:**
- Do not use as a substitute for proving the base case.
- Do not assume finiteness preservation holds for an operation other than insert without an appropriate lemma.

<a id="verus-global-014"></a>

## verus_global_014 — Set function equality by empty/nonempty case split and induction

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Proving equality between a recursive set function and a high-level operation like `s.map(f)`, with induction on a smaller set.

**Obstacle:** Direct induction over the whole set is not readily applied; the empty base case and nonempty recursive case must be separated.

**Mechanism:** Split on `s.is_empty()`, unfold definitions in the empty branch, and use the induction hypothesis on `s.remove(x)` in the nonempty branch.

**Procedure:**
1. Split on `s.is_empty()`.
2. In the empty branch, unfold `Set::empty` and the function definitions to prove both sides equal the empty set.
3. In the nonempty branch, choose a removed element and apply the induction hypothesis to the smaller set.
4. Use the induction hypothesis to close the recursive equality.

**Why:** The empty/nonempty split exposes a definitional base case and makes the induction hypothesis directly applicable to a smaller set.

**Check:** Ensure the recursive function removes a chosen element so that the smaller-set relation is available for induction.

**Avoid or stop:**
- Only applicable when the recursion removes a chosen element; if not, adapt the smaller-set argument.
- Avoid using the empty branch as a general simplification if definitions do not unfold.

<a id="verus-global-015"></a>

## verus_global_015 — Set equality by choose-based witness extraction inside membership forall

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Proving `setA == setB` or `setA =~= setB` for compound finite-set expressions, especially when one side's membership condition is existential and built-in macros such as `assert_sets_equal!` fail or Verus does not automatically apply set extensionality.

**Obstacle:** The SMT solver does not derive set equality from bidirectional membership on its own; when a membership direction is existential, no concrete witness is available unless explicitly chosen with `choose`, so the witness facts must be named and propagated.

**Mechanism:** Explicitly prove both directions of containment or a membership equivalence with guarded implications and `choose`-extracted witnesses, then close with an explicit `setA =~= setB` assertion to invoke set extensionality.

**Procedure:**
1. Write `assert forall|y| left_set.contains(y) == right_set.contains(y) by { ... }` or the two directional containment asserts.
2. In the left-to-right direction, assume `left_set.contains(y)` (for example with `if left_set.contains(y) { ... }` or an implication proof).
3. If the right side's membership condition is existential, extract a concrete witness with `let a = choose|a: SomeType| condition(a);` and assert the witness properties required by the condition.
4. Use `assert` to propagate the witness-based membership fact to the other side.
5. Write the reverse direction similarly: assume `right_set.contains(y)`, and if necessary choose a witness for the left-side membership.
6. Complete the forall or containment proof, then assert `left_set =~= right_set` or `assert(left_set =~= right_set)` to close the equality by set extensionality.

**Why:** The source cards solve equality by making membership reasoning explicit, extracting choose-based existential witnesses to propagate membership facts, and applying extensionality as the final bridge when built-in set equality automation fails.

**Check:** Ensure both containment directions are proved before asserting extensionality; the set equality lemma verifies with the `choose` witness extraction and without `assert_sets_equal!` or set-internals reasoning; for existential directions, assert that the chosen witness has the required properties.

**Avoid or stop:**
- Do not use for subset-only goals unless the reverse direction is also required.
- Do not assert equality after proving only one containment direction.
- Do not use for simple set equality where no existential witness extraction is needed.
- Do not use for recursive or fold recurrence definitions; this is for set-map or insert-style existentials.

<a id="verus-global-016"></a>

## verus_global_016 — Prove subset relations involving derived sets by explicit forall, guarded implications, and existential witness reuse

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Proving `s.subset_of(flatten_sets(sets))` or similar subset relationships involving a derived set, where automatic unfolding is insufficient.

**Obstacle:** The subset relation requires both a universal membership implication and, for flatten-like definitions, an existential witness in the flattened set; the solver does not automatically identify the witness or use the outer bound variable.

**Mechanism:** Introduce an explicit `assert forall` for the membership implication, guard the antecedent with `if` inside the body, and reuse the outer bound set as the existential witness for flatten membership.

**Procedure:**
1. Replace the empty proof body with an explicit `assert forall|e: A| s.contains(e) implies flatten_sets(sets).contains(e) by { ... }`.
2. Inside the body, use `if s.contains(e) { ... }` to make the antecedent available.
3. Let the solver use the definition of `flatten_sets` or explicitly assert the existential membership.
4. For a quantified set `s` in `sets`, assert `exists|s_witness| sets.contains(s_witness) && s_witness.contains(e)` with `s_witness` bound to `s` itself.
5. Close the subset goal from the discharged forall.

**Why:** The source cards make the subset proof explicit and provide the existential witness directly, avoiding reliance on automatic rewriting or choosing a new witness.

**Check:** Ensure the outer quantified set is actually a valid witness for the existential; otherwise use a more general witness extraction technique.

**Avoid or stop:**
- If the desired witness is not one of the outer quantified sets, more general choose/witness reasoning may be needed.
- Do not use this as a replacement for set equality when both containment directions are required.

<a id="verus-global-017"></a>

## verus_global_017 — Relate sequence-derived sets by index witnesses and case splits

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Proving membership or equality between sequence-derived sets across tail decomposition or push, using explicit sequence index witnesses.

**Obstacle:** The solver cannot map between set membership and sequence indices across sequence transformations such as tail and push.

**Mechanism:** Obtain an index witness with `choose` or `exists`, case split on whether the index is in the existing part or the transformed element, and assert bounds and equations to transfer membership.

**Procedure:**
1. For a set membership claim about a sequence-derived set, obtain an index `i` satisfying `0 <= i < s.len() && s[i] == x` using `choose` or `exists`.
2. Case split on the position of `i` relative to the sequence operation, such as `i < s.len()` versus `i == s.len()` for push, or first versus tail for a decomposition.
3. If the index maps into an existing subrange, assert the corresponding index equation such as `rest[idx-1] == s[idx]` and the bounds `0 <= idx-1 < rest.len()`.
4. If the index is the added or last element, assert the equality `y == x` from the sequence operation.
5. For the reverse direction, choose an index in the simpler sequence and assert it remains valid in the transformed sequence.

**Why:** The source cards succeed by reducing set membership to sequence indices and then explicitly splitting cases around the sequence operation, which gives the solver the concrete index facts it needs.

**Check:** Ensure the index bounds and equations are asserted in both directions; otherwise the solver may not connect the set membership to the sequence position.

**Avoid or stop:**
- Do not use index splitting when set membership is already available directly.
- Avoid if the sequence operation is not push/tail and the index mapping cannot be expressed cleanly.

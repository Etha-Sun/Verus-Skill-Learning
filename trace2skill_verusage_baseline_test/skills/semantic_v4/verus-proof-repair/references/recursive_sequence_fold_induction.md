# Recursive Sequence and Fold Induction

**Consult when:** The proof is stuck on fold_left/prefix-last decomposition, elementwise lifting through folds, sequence-filter recurrences, push/mutation subrange-fold closure, or index-dependent recursive helpers over sequences.

**Do not consult when:** The goal only needs set equality, structural wrapper decomposition, or post-loop universal closure without a recursive recurrence.

<a id="verus-global-018"></a>

## verus_global_018 — Fold-left sequence equality by recursion-aware length induction and prefix/last decomposition

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Verus must prove an equality or equivalence involving Seq::fold_left over a whole sequence, a prefix/last decomposition, or two elementwise-equivalent sequences; the necessary connection is not discharged by SMT after unfolding or solver tuning.

**Obstacle:** fold_left and analogous recursive sequence definitions do not match the common front/tail left-fold mental model; asserting first + rest decomposition or unproven prefix fold recurrences leaves the solver without a certificate, causing persistent postcondition failures.

**Mechanism:** Inspect the recursive definition, then perform induction on sequence length using the definitional decomposition such as take(len-1)/last() or drop_last()/last(). Recursively apply the lemma to the shorter prefix, assert the exact prefix-reassembly fact such as prefix.push(last) == seq or concat length additivity, and rewrite the full fold expression in terms of the prefix before applying the induction hypothesis.

**Procedure:**
1. Reveal the fold/sequence function definition, for example with by(compute_only) or source inspection, before committing to an induction direction.
2. Add a termination/decreases measure appropriate to sequence length.
3. For a nonempty sequence, construct the initial segment as s.take(s.len()-1) or s.subrange(0, s.len()-1) and the final element as s.last().
4. Recursively call the lemma on the shorter initial segment.
5. Assert the reassembly equality such as s_prefix.push(s.last()) == s and the fold rewrite from the full sequence to the prefix.
6. Chain the induction hypothesis with the reassembly equality to close the full sequence goal; for equivalence over two sequences, assert that the final elements satisfy the equivalence predicate.

**Why:** Success memories from fold-left append/len/associativity/equivalence all used this decomposition after failures showed front/tail assertions could not be proved; the failure memories explicitly identify mismatch between assumed left-fold and actual drop_last/last recursion as the root cause.

**Check:** The inductive step must mirror the actual recursive equation; if a front/tail assertion repeatedly fails, stop and inspect the definition rather than adding more assertions or increasing rlimit.

**Avoid or stop:**
- Do not assert s == seq![first] + rest or use front/tail induction for fold_left unless the revealed definition supports it.
- Do not assume unproven decomposition lemmas such as fold_left(s.prefix(n+1)) == fold_left(s.prefix(n)) + s[n]; prove them or restructure the argument.
- Avoid assertion bloat and solver-tuning loops when the induction direction is the actual problem.

<a id="verus-global-019"></a>

## verus_global_019 — Lift elementwise sequence equivalence through fold using an existing fold equivalence lemma

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A postcondition or proof goal has already established elementwise equivalence between two sequence arguments and must use it to prove equality of the results of a fold or accumulation operation.

**Obstacle:** The SMT solver does not automatically lift an elementwise relation through an accumulator fold to equality of accumulated results.

**Mechanism:** Instantiate an existing fold equivalence lemma with a closure that captures the elementwise equivalence and the fold accumulator; prove the elementwise closure, then apply the lemma to the two full sequences.

**Procedure:**
1. Define an equivalence closure over elements that calls the already-proved elementwise relation.
2. Define an accumulator closure corresponding to the fold operation used in the goal.
3. Prove or cite the fact that the equivalence closure holds pairwise for the source sequence elements.
4. Call the existing fold equivalence lemma with both sequences, the equivalence closure, the initial value, and the accumulation closure.
5. Use the returned fold-result equality to discharge the postcondition.

**Why:** The only success memory for this trajectory shows direct use of a library lemma to close a ghost_serialize postcondition without manually decomposing the fold.

**Check:** The lemma statement must match the goal; if the goal uses a subrange or prefix rather than the full sequences, first assert the exact connecting equalities or choose a different lemma.

**Avoid or stop:**
- Do not manually unfold the fold when an existing fold equivalence lemma already matches the full-sequence goal.
- Do not use this for pointwise equality without an accumulator/fold target.

<a id="verus-global-020"></a>

## verus_global_020 — Isolate missing sequence-filter recurrences into atomic test lemmas

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A proof about Seq::filter is stuck on a recursive head/tail or singleton/empty base-case equality such as s.filter(pred) == s.skip(1).filter(pred) or seq![x].filter(pred), despite repeated reasoning, broadcast axioms, fuel changes, or manual assertions.

**Obstacle:** The available filter axioms and solver triggers do not justify the expected filter-to-tail or singleton recurrence, so the full induction step cannot be closed.

**Mechanism:** Treat the stuck recurrence as a missing lemma rather than a solver-tuning problem. Extract the exact atomic recurrence or base-case behavior from the main proof, test it as an independent small lemma or explicit assertion, and use the outcome to discover whether the fact is provable, requires a different decomposition, or should be avoided.

**Procedure:**
1. Stop varying fuel, rlimit, or broadcast placement after repeated failures of the same full-lemma skeleton.
2. Write the expected recurrence explicitly as an assertion or small helper lemma, for example seq![x].filter(pred) == Seq::empty() under !pred(x).
3. Test the atomic base case independently before proving the whole inductive lemma.
4. If the atomic fact fails, inspect available library lemmas and consider a different decomposition such as subrange, contradiction on filtered length, or explicit quantifier triggers.
5. If a separate lemma succeeds, use it to replace the unproved linking assertion in the main induction.

**Why:** Multiple failure trajectories show the same core issue: the agent repeatedly attempted minor variations of unprovable filter-skip links but did not isolate the missing atomic recurrence; the failure memories consistently identify isolation and explicit small tests as the missed recovery step.

**Check:** A valid filter recurrence or base case should be provable as a separate lemma before being used in the full proof; if it is not, the main proof cannot rely on it.

**Avoid or stop:**
- Do not present an unverified proposed filter recurrence as a verifier-confirmed lemma.
- Do not keep tuning rlimit, fuel, or broadcast placement when the same decomposition remains unproved.
- Do not assume filter distributes over head/tail or concat without proving the specific instance.

<a id="verus-global-021"></a>

## verus_global_021 — Use ghost snapshots and subrange extension equalities for push/mutation spec-view closure

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** After an executable mutation such as Vec::push, or a step that mutates a buffer, vector, or `self`, a proof must re-establish equality of an abstract ghost view, a subrange, or a folded serialization with a specification-side sequence, or preserve old-state preservation and new-state/suffix equality against a spec accumulator.

**Obstacle:** Verus does not automatically update ghost views after push or successive mutations/calls, and does not automatically connect a lemma stated for whole sequences or subranges to the exact old/new subrange equality required by the invariant; the solver cannot see the relation between old and new values after mutation.

**Mechanism:** Take `let ghost` snapshots immediately before the first mutation and after each relevant step; use explicit collection-update lemmas for the immediate push effect, then bridge higher-level goals with atomic subrange, concatenation, or direct equality assertions between snapshots and spec-level accumulators. If applying a fold lemma, assert the exact subrange-prefix and element-index equalities that match the lemma statement, then chain those equalities with the lemma result.

**Procedure:**
1. Before any mutation, bind a ghost pre-state snapshot of the value, buffer, or vector view.
2. After the first mutation or call, bind a mid-state snapshot if later assertions need it.
3. For an immediate post-push ghost-view equality, use a collection-update lemma such as Vec::lemma_push rather than leaving an empty proof block.
4. Assert preservation of the previous prefix by relating the new view to the pre-state snapshot with subrange or direct equality.
5. Assert the old/new subrange extension equality in the executable view, and assert the analogous subrange or suffix equality on the specification-side sequence.
6. If a fold or other sequence lemma is used, first assert the exact subrange-to-prefix and element-index equalities required to match the lemma statement to the goal.
7. Assert that the newly appended suffix equals the corresponding spec computation, such as the sub-serializer's ghost output.
8. For multi-step appends, combine prefix and suffix equalities with sequence operations such as `subrange`, `+`, and `=~=`, or chain the atomic equalities with the lemma result, to re-establish the invariant before leaving the loop body or returning.

**Why:** Three failure trajectories demonstrate that empty proof blocks and single lemma calls fail unless Verus is given either the collection-update fact for push or the explicit connecting equalities between old/new subranges and fold arguments; explicit snapshots make incremental state changes visible to the solver and reduce dependence on re-discovering old/new relations or obscure lemma behavior.

**Check:** Every post-mutation proof obligation about old or new state mentions a named snapshot rather than a mutable access, and after push the invariant proof contains an explicit old-to-new subrange or fold equality chain; no empty proof block claims v@ == seq![x] without a collection lemma.

**Avoid or stop:**
- Do not leave empty proof blocks for sequence singleton equalities after push.
- Do not expect a fold lemma stated for a full sequence to apply to subrange(0,i+1) unless the subrange-prefix and element-index equalities are asserted explicitly.
- Avoid weak invariants that do not record the exact subrange being accumulated.
- Do not rely on the old value after mutation without a pre-mutation snapshot.
- Do not assert a suffix equality without connecting it to the exact spec function being verified.

<a id="verus-global-022"></a>

## verus_global_022 — Prove index-dependent list or sequence properties by isolated helper induction on the index

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A target lemma must establish a property of list[k] or seq[k] parameterized by index k, given a sequentiality or order relation and a base element precondition.

**Obstacle:** The main proof would be cluttered if it attempted index induction inline; Verus needs a separate recursive helper whose decreasing argument is the index to check termination cleanly.

**Mechanism:** Introduce a helper lemma that recurses on k-1; the base case uses the first-element precondition, and the inductive case uses the sequentiality predicate to lift the property from k-1 to k.

**Procedure:**
1. Identify the index-dependent property as a separate lemma statement over the index.
2. Make the helper call itself on k-1 with an explicit decreases k or equivalent termination measure.
3. Prove the base case k == 0 from the known first element or sequence property.
4. In the inductive case, use the sequentiality or order predicate to relate the k-1 result to the k result.
5. Call the helper from the main lemma on the desired index.

**Why:** The only success memory for index-dependent sequential-list properties shows that isolating helper induction on the index keeps the main lemma clean and satisfies Verus termination checking.

**Check:** The helper's decreasing argument must be the index and the base case must be discharged from preconditions rather than an empty sequence.

**Avoid or stop:**
- Do not inline the index induction inside a complex main proof if a separate helper can produce the same quantified fact.
- Do not assume the property lifts from k-1 to k; explicitly use the sequentiality or order predicate.

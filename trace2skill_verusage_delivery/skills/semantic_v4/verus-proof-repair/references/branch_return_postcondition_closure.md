# Branch, Exit, and Return-Point Postcondition Closure

**Consult when:** The top-level ensures remains unproved at a specific return path, an early false return refutes a global predicate, a no-field constructor branch reduces trivially, or an Option-valued postcondition must be split before unwrap.

**Do not consult when:** The proof needs a structural component lemma or loop invariant; return-site assertions are secondary.

<a id="verus-global-047"></a>

## verus_global_047 — Close top-level ensures at each return with branch-specific assertions

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Function postcondition is a named predicate or disjunction depending on branch state, and branch-specific facts have already been proved but the top-level ensures remains unproved at return.

**Obstacle:** Branch facts are local and discharged, but the verifier still reports `postcondition not satisfied` at return because there is no proof block that connects those facts to the named or disjunctive ensures.

**Mechanism:** At each return site, assert the exact top-level predicate or the branch-specific disjunct in terms of the current local state. This supplies the missing bridge from already-proved branch facts to the ensures obligation by giving Verus the required postcondition shape.

**Procedure:**
1. At the start of each return path, identify which disjunct or predicate of the function's ensures clause should hold for that path.
2. Before the return, assert the exact top-level ensures predicate or its branch-specific alternative using the current local state and the branch facts already proved.
3. For named or abstract postcondition predicates, add a final assert or proof block at each return showing that accumulated branch facts imply the top-level predicate; do not assume Verus will combine branch facts implicitly.
4. Re-run verification and ensure no `postcondition not satisfied` error remains at any return.

**Why:** Success memory shows that asserting the ensures alternative before returns, using the current empty sequence and set shape, discharges conditional postconditions. Failure memory from the related trajectory shows that proving branch-internal sub-specification facts alone leaves the top-level ensures unproved; the missing step is exactly the return-site closure.

**Check:** No `postcondition not satisfied` error remains at any return, and each return path is preceded by an assertion that instantiates the relevant ensures alternative or top-level predicate with the current local state.

**Avoid or stop:**
- Do not use when the postcondition is universally quantified over an arbitrary returned value and cannot be named at the return.
- Do not confuse proving branch-internal facts with proving the function ensures; the verifier will not infer top-level closure from branch lemmas automatically.
- Do not assert a postcondition predicate unless the current return path actually satisfies it.

<a id="verus-global-048"></a>

## verus_global_048 — Discharge early false return by asserting concrete counterexample and negated global postcondition

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Function has an early `return false` when a local counterexample violates an aggregate postcondition, and the ensures clause is a global predicate that must be shown not to hold.

**Obstacle:** Local counterexample violation is established inside the function or loop but is not automatically linked to the global postcondition predicate, so the early false return does not discharge the ensures obligation.

**Mechanism:** At the early false return site, assert the concrete local violation and then assert the negation of the global postcondition. This converts the local observation into a global refutation that satisfies the ensures branch.

**Procedure:**
1. At the early `return false` site, identify the concrete counterexample value or pair and the local predicate it violates.
2. Assert the local violation explicitly, for example that the ordering or membership predicate is false for the concrete counterexample.
3. Assert the negation of the global postcondition for the current counterexample value.
4. Return false and let the verifier use the asserted global negation to close the early exit branch.

**Why:** The success memory shows that the verifier does not connect a local counterexample to the aggregate global property without an explicit bridge. Adding both the local violation assertion and the negated global postcondition gives the exact shape needed to close the early false return.

**Check:** The verifier accepts the early false return without postcondition errors, and both a local violation assertion and a negated global postcondition assertion are present before the return.

**Avoid or stop:**
- Do not use for early returns that must satisfy a positive postcondition; there assert the satisfied branch-specific predicate rather than its negation.
- Do not assert the negated global postcondition unless the concrete local violation has first been proved.

<a id="verus-global-049"></a>

## verus_global_049 — Leave no-field constructor branches empty when postconditions reduce to the same constant

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Case-analysis branch matches a no-field constructor on both sides, and postcondition equalities reduce to identical constructor constants.

**Obstacle:** The postcondition may appear to require equality proof in a branch, but for constant-like no-field constructors both sides are the same closed value.

**Mechanism:** Let the constructor's constant-like definition reduce both sides of the postcondition to identical values, allowing Verus to discharge the branch automatically without explicit assertions or lemma calls.

**Procedure:**
1. In the case-analysis arm, identify that both sides use the same no-field constructor.
2. Compute both sides of each postcondition equality for that constructor and confirm they reduce to the same constructor constant.
3. Leave the branch empty if the expressions reduce to identical constants; do not add unnecessary explicit assertions or lemma calls.
4. Add an explicit assertion only if the equality does not reduce to identical constructor values.

**Why:** The success memory shows that in a no-field constructor branch the relevant equalities reduce to true equality, so the SMT solver discharges them automatically. An empty branch is sufficient and avoids proof noise.

**Check:** The branch is accepted by the verifier with no additional proof code, and the postcondition equality reduces to an identical constructor constant on both sides.

**Avoid or stop:**
- Do not use if the constructors carry fields that affect the asserted equality.
- Do not use if other branch obligations remain unproved; only the constant-like equality closure is automatic.

<a id="verus-global-050"></a>

## verus_global_050 — Split Option-valued postcondition into Some and None branches before unwrapping

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** External-body or function ensures refers to an Option value through unwrap and must be defined for both Some and None cases.

**Obstacle:** Using unwrap in an unbranched ensures is not well-defined for the None case, causing postcondition failure or an ill-defined specification.

**Mechanism:** Split the ensures into `opt is Some` and `opt is None` branches so that unwrap occurs only under the `Some` branch. Express the None-branch property in an unwrap-free alternative such as a `forall`.

**Procedure:**
1. When the ensures clause refers to an Option value via unwrap, do not leave the unwrap in an unconditional ensures.
2. Split the ensures into `opt is Some` and `opt is None` branches.
3. Use unwrap only under the `Some` branch where it is safe.
4. For the `None` branch, express the required relationship without unwrapping, for example with a `forall` or an alternative predicate.
5. Verify that the split branches together preserve the original intended postcondition relationship.

**Why:** The success memory shows that the original postcondition failed because unwrap was used when the Option value could be None. Splitting the ensures makes the specification well-defined in Verus while still capturing the required relationship in both cases.

**Check:** The ensures clause is accepted by Verus, unwrap appears only under a `Some` branch, and the `None` branch has an unwrap-free statement of the intended property.

**Avoid or stop:**
- Do not keep unwrap in a context where the Option may be None.
- Do not split the postcondition in a way that loses the original relationship across the Some and None cases.

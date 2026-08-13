# Structural Decomposition for Option, Struct, Enum, and Composite Properties

**Consult when:** A wrapper/sum type needs constructor case split with inner lemmas, a product/struct property delegates to components, bidirectional structural equivalence is needed, or a combined postcondition must be decomposed field-wise.

**Do not consult when:** The issue is specifically serialization length/tag decomposition or fixed-width byte lemmas; use the serialization reference unless the only obstacle is wrapper/product structure.

<a id="verus-global-051"></a>

## verus_global_051 — Option-like wrapper/sum case split with inner component lemma and tag contradiction

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A wrapper or tagged-sum type with two constructors, such as Option<T>, defines or serializes a structural predicate, equality, symmetry, prefix, or injectivity property by case analysis over the constructors and reduces to an inner component property in the matching constructor arm. The wrapper-level goal may involve equality, symmetry, serialization equality, prefix non-membership, or injection from full serializations, and its proof depends on the inner type T.

**Obstacle:** The solver does not automatically perform the wrapper-level constructor case split and apply an existing inner component lemma. For serialization, prefix, or injectivity goals, mixed variants must also be distinguished by an explicit leading discriminant or tag-byte fact, such as 0 for None and 1 for Some, and the matching recursive arm must be reduced to the inner lemma or inductive assumption before the outer goal closes.

**Mechanism:** Exhaustively match the two wrapper/sum values together. In mismatched or empty arms, discharge the goal from the predicate or encoding definition, or by the explicit leading discriminant/tag-byte inequality. In the matching constructor arm, extract the inner values and, if the encoding includes a leading tag byte, separate that tag byte from the inner encoding by subrange reasoning. Then invoke the corresponding inner component or recursive lemma for symmetry, same-views serialization equality, prefix non-membership, or payload injectivity, and let the solver lift the inner fact to the wrapper-level goal.

**Procedure:**
1. Exhaustively match the two values together, covering the same-constructor arms and all mismatched-constructor arms, such as (None,None), (Some,Some), (None,Some), and (Some,None).
2. Discharge contradictory or empty/mismatched arms from the outer preconditions or wrapper predicate/encoding definition; for serialization, prefix, or injectivity goals, assert or rely on the leading discriminant/tag bytes, such as 0 for None and 1 for Some, and use their inequality to close mixed arms.
3. In the matching constructor arm, extract the inner values and, if the encoding has a leading tag byte, use subrange reasoning to separate the tag from the serialized inner value.
4. Invoke the corresponding inner component or recursive lemma, such as symmetry, same-views-serialize-the-same, serialization-is-not-a-prefix-of, or serialize-injective, on the extracted inner values with preconditions satisfied from branch hypotheses or outer preconditions.
5. Let the solver reduce the wrapper-level predicate, equality, prefix, or injectivity goal to the inner fact just proved; avoid manually reproving the inner property if an existing lemma already matches the current branch.

**Why:** This works because proof branching is aligned with the wrapper predicate or encoding definition. The matching constructor arm uses an existing inner component lemma to supply exactly the component-level fact, while mixed or empty arms are closed by definition or by an explicit discriminant/tag-byte contradiction, avoiding separate manual proof effort for each variant combination.

**Check:** Each match arm is either discharged by contradiction or definition, or contains an inner/recursive lemma call whose preconditions are visibly available from branch hypotheses or outer preconditions. For mixed serialization, injectivity, and prefix arms, the leading tag or discriminant-byte inequality is made explicit before the arm closes.

**Avoid or stop:**
- Not for wrapper predicates or encodings that are opaque or not definitionally reducible by constructor case.
- Not when the required inner lemma does not exist or its preconditions cannot be derived from the current branch or outer context.
- Not for wrapper-specific facts that depend on data outside the inner component predicate unless branch-specific facts are explicitly asserted.
- Not for encodings without a fixed discriminant or with ambiguous variable-length prefixes.
- Do not split only one value when two tagged-sum values are involved; mixed cases require explicitly exposing the tag-byte or constructor-discriminant contradiction.

<a id="verus-global-052"></a>

## verus_global_052 — Composite product type component-wise lemma delegation

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A composite product type such as a tuple or multi-field struct defines a structural predicate, equality, serialization relation, or view relation component-wise. A lemma or property is already known for each component type, and the goal is to prove the same property for the composite type by delegating to those component lemmas.

**Obstacle:** The solver does not automatically split the composite predicate into component facts. Without explicit component lemma calls, the whole-type equality or property remains open even though each component-level property is already provable; this also applies to serialization-equality goals where field-level lemmas are known.

**Mechanism:** Invoke the corresponding component lemma on every relevant field or tuple projection. The composite predicate definition reduces the whole-type relation to a conjunction or pair of component relations, so the solver combines the component results and lifts them to the composite goal. For serialization equality, delegate to already-proved field serialization lemmas and compose the derived field equalities into the whole-type serialization obligation.

**Procedure:**
1. Identify the composite product type and each component or field that appears in the composite predicate definition for which a component lemma already exists.
2. For tuple and struct types, project the relevant components of the left and right values, such as self.0/other.0 and self.1/other.1, or the corresponding named fields.
3. Call the corresponding component lemma on every required projection; for serialization-equality goals, invoke the already-proved serialization lemma for each field or inner component and compose the derived equalities.
4. Ensure every component is covered, each component lemma call is type-correct, and all component lemma preconditions are available in the composite proof context.
5. If the only missing proof evidence was the component lemma calls, insert exactly those calls and re-run the verifier to confirm closure through the composite predicate definition.

**Why:** This directly leverages the composite type's definitional decomposition and existing component lemmas instead of re-proving known component properties or manually expanding the structure. It reuses verified component invariants for serialization equality, but one serialization source is recorded as failure_memory, so that specialization should be validated before being treated as a confirmed success.

**Check:** Every component has a corresponding lemma call, each call is type-correct and has its preconditions available, and after insertion the composite predicate definition is reducible to those component facts. For serialization equality, verify that the field-level lemmas close the whole-type obligation in the exact form rather than assuming derived preconditions close automatically.

**Avoid or stop:**
- Not for composite predicates that are not defined component-wise.
- Not when component lemmas require stronger preconditions than are available in the composite proof context.
- Not for proving new component facts; this only lifts already established component lemmas to the whole.
- Do not assume field-level lemmas automatically close whole-type marshalable or derived preconditions; they only support the property they already prove, such as serialization equality.

<a id="verus-global-053"></a>

## verus_global_053 — Bidirectional structural equivalence by explicit implication splitting

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A structural equivalence relation or predicate is defined by a structural size fact plus an elementwise or componentwise condition. The goal is to prove symmetry of the predicate, typically as a boolean equality between P(self, other) and P(other, self).

**Obstacle:** The solver does not automatically split the boolean equivalence into two implication directions, and the elementwise condition remains hidden inside the predicate definition without explicit pointwise reasoning.

**Mechanism:** Split the goal into forward and backward implication branches. In each branch, first derive the structural size equality, then assert the elementwise condition using a quantified pointwise proof block that references already proven component or elementwise symmetry. Finally assert the target predicate inside each branch.

**Procedure:**
1. Write separate implication blocks for the two directions of the equivalence.
2. In each branch, assert the structural size fact such as length equality immediately from the hypothesis.
3. Assert the elementwise or componentwise condition using a forall quantifier with a trigger, using a by block to cite the existing component symmetry or equality lemma.
4. Conclude the target predicate inside each branch to obtain the overall boolean equivalence.

**Why:** This gives the solver two separate proof states, each with the needed directional hypothesis, and exposes the structural and elementwise components of the predicate one at a time so already proven component facts can be applied.

**Check:** Both implication directions are syntactically present, the quantified pointwise assertion has a trigger, and the branch-specific component lemma is actually applied for each element or component.

**Avoid or stop:**
- Not necessary when the solver can close the equivalence directly by definition.
- Not for opaque predicates without an assertable structural size and elementwise decomposition.
- Not for one-directional implications only; this targets bidirectional structural equivalence.

<a id="verus-global-054"></a>

## verus_global_054 — Decompose combined abstract-state and invariant postconditions into sequential field-wise blocks

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A function or constructor postcondition combines an abstract state specification predicate and a structural invariant over a concrete state type with an abstract view projection. The proof must establish argument-derived facts, invariant satisfaction, and field-wise equality with the abstract specification.

**Obstacle:** The combined postcondition has multiple clauses of different kinds, and a monolithic proof does not localize failures or provide the solver with clear field-wise equality and invariant conjunct facts.

**Mechanism:** Break the proof into sequential blocks: first derive argument or parser facts, then prove each invariant conjunct individually using subcomponent postconditions and view equalities, and finally assert field-wise equality between the concrete state's abstract view and the expected abstract state.

**Procedure:**
1. Assert or derive the argument-derived facts needed for later proof blocks.
2. Prove the structural invariant predicate by asserting each conjunct individually, citing subcomponent constructor postconditions and view equalities.
3. Prove the abstract state specification by asserting field-wise equality between the concrete state's abstract projection and the expected abstract state.
4. If a block fails, localize the missing fact or equality in that block rather than reverting to a monolithic proof.

**Why:** Sequential blocks mirror the syntactic clauses of the combined postcondition, reducing a large obligation into independently checkable subgoals and making failures easier to diagnose.

**Check:** Every syntactic conjunct of the combined postcondition is explicitly covered by at least one assertion or derived fact, and every field of the abstract state is matched by an equality.

**Avoid or stop:**
- Not for a single opaque postcondition predicate that cannot be decomposed into argument, invariant, and field-wise equality parts.
- Not when the invariant and abstract state specification are mutually dependent and must be proven simultaneously rather than sequentially.
- Not for branch, exit, or return-point closure of function postconditions rather than the structural specification itself.

<a id="verus-global-055"></a>

## verus_global_055 — Establish structural well-formedness via empty auxiliary collections and per-element predicate

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A result or state struct has auxiliary collection fields and an active collection field. A structural well-formedness predicate is satisfied by setting the auxiliary collections to empty and proving a per-element variant predicate over the active collection.

**Obstacle:** The solver must know that empty auxiliary collections vacuous satisfy their per-element conditions and that every element of the active collection satisfies the required variant predicate before discharging the well-formedness predicate.

**Mechanism:** Construct the struct with the auxiliary collection fields explicitly empty. In a proof block, assert that their lengths are zero, assert or derive that every element in the active collection satisfies the per-element predicate, and then derive the structural well-formedness predicate from those facts.

**Procedure:**
1. Construct the result struct with the auxiliary collection fields explicitly set to empty collections.
2. In a proof block, assert that the lengths of the auxiliary collections are zero.
3. Assert or derive that every element in the active collection satisfies the required per-element variant predicate.
4. Use the emptiness facts and the per-element predicate facts to discharge the structural well-formedness predicate.

**Why:** This separates vacuous structural checks on empty collections from the non-vacuous per-element check on the active collection, giving the solver exactly the facts that define the well-formedness predicate.

**Check:** The auxiliary collections are empty, their zero lengths are asserted, the active collection has a proven or derived per-element predicate, and the well-formedness predicate is explicitly derived from those facts.

**Avoid or stop:**
- Not for non-empty auxiliary collections or when the per-element predicate must also hold on auxiliary collections.
- Not if the well-formedness predicate has additional clauses beyond emptiness and per-element predicates.
- Not for general pointwise extensional reasoning over arbitrary sets or sequences beyond the structural well-formedness target.

# Serialization, Marshalability, Prefix, and Size-Bound Proofs

**Consult when:** The goal involves fixed-width integer roundtrips, wrapper serialization delegation, tag/prefix/suffix segment equalities, concatenated prefix component equalities, vector injectivity by element induction, component prefix inequality, marshalable size bounds, or derived is_marshalable macro lemmas.

**Do not consult when:** The goal is only generic set/sequence equality, trigger selection, or structural wrapper decomposition with no byte-level/tag reasoning.

<a id="verus-global-056"></a>

## verus_global_056 — Fixed-width integer serialization roundtrip equality and contradiction

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Proof goal involves `spec_u64_to_le_bytes` / `spec_u64_from_le_bytes` or an analogous fixed-width integer serializer, and requires equality or contradiction from serialized bytes.

**Obstacle:** Verus does not automatically connect serialization and deserialization: it lacks the roundtrip equality `spec_u64_from_le_bytes(spec_u64_to_le_bytes(v)) == v` and the fixed-length fact unless explicitly introduced.

**Mechanism:** Invoke `vstd::bytes::lemma_auto_spec_u64_to_from_le_bytes()` or the analogous integer-width lemma, then make the serialization/deserialization equality chain explicit so that serialized equality propagates to value/view equality or closes a contradiction.

**Procedure:**
1. Identify the concrete fixed-width serializer/deserializer pair in the obligation, such as `spec_u64_to_le_bytes` and `spec_u64_from_le_bytes`.
2. Call `lemma_auto_spec_u64_to_from_le_bytes()` for each relevant value before performing byte-level equality reasoning.
3. Assert `spec_u64_from_le_bytes(spec_u64_to_le_bytes(v)) == v` and the reverse orientation as useful for the values under study.
4. When equality of serializations is assumed, assert equality of the deserialized values, then derive equality of the original values or `view_equal`.
5. If the goal is `assert(false)`, write the intermediate equality chain before it: serialized equality -> deserialized equality -> original value equality -> contradiction with the precondition.

**Why:** Explicit roundtrip and equality assertions provide the ground terms Verus needs; otherwise the SMT solver cannot infer the contradiction or injectivity property from the byte-level definitions alone.

**Check:** The SMT solver should close the goal without additional byte-index reasoning, provided the selected lemma matches the integer width used in `ghost_serialize`.

**Avoid or stop:**
- Do not use this as the sole mechanism when the serialization includes variable-length prefixes, tags, or concatenated components.
- Do not assume the lemma automatically covers casts or wrappers; conversion steps may need a separate wrapper-lemma proof.

<a id="verus-global-057"></a>

## verus_global_057 — Wrapper serialization proof by delegating to the inner type

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A wrapper type's `ghost_serialize` or serialization lemma is defined by converting to an inner type and reusing that inner type's serialization, such as `usize` cast to `u64`.

**Obstacle:** The verifier does not automatically reduce properties of the wrapper to properties of the inner representation; an existing inner-type lemma is not applied unless the intermediate conversion values are exposed.

**Mechanism:** Bind the exact intermediate representation used by the wrapper's serialization, invoke the inner type's verified lemma on those intermediates, and lift the result back to the wrapper equality, non-prefix, or injectivity property.

**Procedure:**
1. Inspect the wrapper's `ghost_serialize` definition to identify the conversion and the inner serializer, for example `(*self as u64).ghost_serialize()`.
2. For each wrapper value, bind the exact intermediate term used by that definition, such as `let v_u64 = v as u64`.
3. Invoke the already-verified inner-type lemma, such as injectivity or serialization non-prefix, on those intermediate terms.
4. Lift the inner conclusion back to the wrapper type through the same conversion.

**Why:** This reuses trusted lemmas for the underlying representation and avoids re-proving low-level byte facts for the wrapper.

**Check:** The intermediate terms match the serialization definition exactly, so the inner lemma applies to the same data that the wrapper serialized.

**Avoid or stop:**
- If the wrapper adds tags, lengths, or other concatenated parts, the inner lemma alone is insufficient.
- If the conversion is not injective or not exactly reflected in serialization, this pattern does not apply.

<a id="verus-global-058"></a>

## verus_global_058 — Same views serialize the same via primitive value equality

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Proving `lemma_same_views_serialize_the_same` for a primitive or view-equal type where `view_equal` implies actual equality.

**Obstacle:** Need to obtain serialization equality from `view_equal`; Verus may not automatically lift the view predicate to value equality and then to output equality.

**Mechanism:** First derive `self == other` from `view_equal`, then use value equality to prove that `is_marshalable` and `ghost_serialize` outputs are equal.

**Procedure:**
1. Start with the assumption `self.view_equal(other)`.
2. Assert `self == other` for primitive value-equal types.
3. State that `is_marshalable()` returns the same result for equal values.
4. State that `ghost_serialize()` produces identical output because both calls are applied to equal values.

**Why:** Splitting the proof into value equality and serialization congruence stages is more direct for SMT than trying to derive serialization equality immediately from the view predicate.

**Check:** The verifier closes the goal without external hints.

**Avoid or stop:**
- Do not assume `view_equal` implies value equality for composite or extensional views where the view equivalence is coarser than structural equality.

<a id="verus-global-059"></a>

## verus_global_059 — Serialize postcondition by subrange segment decomposition

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A serialization function appends a tag byte and a recursively serialized value; the proof obligation is that the final data subrange equals the concatenation.

**Obstacle:** Verus needs to see each contiguous segment, including prefix, tag, and suffix, before combining them into the overall sequence equality.

**Mechanism:** Assert the unchanged prefix, tag byte slice, and inner serialization suffix as separate `subrange` equalities, then combine them to prove the overall target equality.

**Procedure:**
1. Identify the serialized output structure: unchanged prefix before the tag, the tag byte slice, and the suffix from recursive serialization.
2. Assert the prefix subrange is unchanged.
3. Assert the tag slice equals `seq![1u8]` or the appropriate discriminator.
4. Assert the suffix equals the inner value's `ghost_serialize()`.
5. Combine the segment equalities to conclude the whole subrange equals `seq![tag] + inner_serialization`.

**Why:** Matching Verus's sequence-concatenation reasoning segment-by-segment avoids the need for external lemmas.

**Check:** The target postcondition is discharged segment-by-segment.

**Avoid or stop:**
- If the serialization is not a simple concatenation, additional index or induction reasoning may be needed.

<a id="verus-global-060"></a>

## verus_global_060 — Concatenated prefix equality via fixed-width length and element-wise indexing

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Given equality of concatenated serializations `a + b == c + d` and a known equal or fixed prefix length, prove component equality `a == c` and `b == d`.

**Obstacle:** The solver may not split concatenated sequences unless it has fixed-size length information and element-wise facts.

**Mechanism:** Use `lemma_auto_spec_u64_to_from_le_bytes` to obtain fixed length 8 for fixed-width prefixes, then assert indexed equalities for an arbitrary prefix index to establish `a == c`, and handle the suffix with offset indices.

**Procedure:**
1. Call `vstd::bytes::lemma_auto_spec_u64_to_from_le_bytes()` to establish that the fixed-width prefix has length 8.
2. For arbitrary `i` in the prefix range, assert `(a + b)[i] == a[i]` and `(c + d)[i] == c[i]`.
3. Use equality of the full concatenations and known prefix length to derive `a[i] == c[i]`, yielding `a == c`.
4. Handle the data suffix symmetrically with indices offset by the prefix length.

**Why:** Element-wise assertions expose prefix relationships to the SMT solver better than deep sequence-algebraic lemmas.

**Check:** The proof closes when prefix equality and suffix equality are both established by indexing.

**Avoid or stop:**
- If prefix lengths are not known equal, obtain a length equality first; fixed-width lemmas only give fixed length for the corresponding fixed-width serializer.

<a id="verus-global-061"></a>

## verus_global_061 — Recover vector injectivity with concrete element induction

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Vector serialization injectivity when generic fold-left sequence reasoning is failing; the proof may be reduced to induction over vector length or element index.

**Obstacle:** Complex generic `fold_left` sequence decompositions did not close; the verifier needs a simpler recurrence and concrete serialization prefix facts.

**Mechanism:** Instead of generic sequence-algebraic lemmas, peel off one vector element at a time by induction, using equality of full serializations to deduce equality of the last element's serialization and known fixed prefix length such as 8 bytes.

**Procedure:**
1. Identify the concrete serialization format of one element and the length-prefix width.
2. Set up induction over vector length or an element index rather than reasoning over `fold_left`.
3. In the inductive step, use equality of the full serializations to extract equality of the last element's serialization.
4. Close the element case with fixed-length serialization facts, then apply the inductive hypothesis to the remaining prefix.

**Why:** This shifts the obligation to a recurrence the SMT solver is more likely to handle. This is a recovery suggestion from a failed trajectory, not a verifier-confirmed success.

**Check:** Before adopting, validate with Verus that the induction is accepted and does not require additional sequence lemmas.

**Avoid or stop:**
- Do not treat this as a verified success; it is a failure-memory recovery pattern.
- If the vector serializer does not have a uniform element layout, induction may still fail.

<a id="verus-global-062"></a>

## verus_global_062 — Lift component prefix inequality to whole concatenated serialization

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Tuple or composite serialization is `s0 + s1`; need to prove whole serialization is not a prefix when a component is not a prefix.

**Obstacle:** Component-level non-prefix inequality does not automatically lift to inequality of the concatenated sequences.

**Mechanism:** Introduce a helper lemma that takes component sequences and lifts a component subrange inequality to inequality of their concatenations. The helper assumes whole concatenations equal and derives a contradiction using a `forall` over the first component's positions. A reverse helper handles the symmetric length asymmetry.

**Procedure:**
1. Define or locate a helper lemma that lifts a component subrange inequality to inequality of the concatenated sequences.
2. For the case where the first component is shorter or longer, invoke the appropriate component's `lemma_serialization_is_not_a_prefix_of` to obtain the component subrange inequality.
3. Supply the length bound for the whole concatenation.
4. Use the helper or reverse helper to conclude the concatenated serialization inequality.

**Why:** The helper encapsulates subrange-extensionality reasoning and keeps the main proof modular.

**Check:** The proof closes when the helper's preconditions exactly match the component inequality and length bound.

**Avoid or stop:**
- Do not use this helper for injectivity length-equality goals without an independent proof of equal component length.

<a id="verus-global-063"></a>

## verus_global_063 — Avoid unproven component-length contradiction in tuple serialize injectivity

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Trying to prove component serialized length equality when concatenated serializations are equal, such as tuple serialize injectivity.

**Obstacle:** The obligation requires proving `s0.len() == o0.len()` from `s0 + s1 == o0 + o1`; an attempted contradiction from `s0.len() < o0.len()` cannot discharge the `!view_equal` precondition.

**Mechanism:** This is a failed route. The prefix lemma relies on a component inequality precondition that is not available for the length case. A different length-equality or arithmetic/indexing proof is required before invoking prefix inequality.

**Procedure:**
1. Do not start with `assert(false)` to rule out length inequality unless a precondition for component inequality is proved.
2. Attempt to derive equal component lengths through fixed-width or serializer-specific length facts first.
3. If those facts are unavailable, search for an alternative constructor or explicit length invariant rather than relying on prefix lemma contradiction.

**Why:** The trajectory repeatedly ended in a rejected `assert(false)`, so this strategy is recorded as a caution.

**Check:** No valid Verus proof emerged for this exact obligation in the source trajectory.

**Avoid or stop:**
- Do not present this as a verifier-confirmed success.

<a id="verus-global-064"></a>

## verus_global_064 — Marshalable size bounds from per-component serialization length arithmetic chain

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Proving `is_marshalable()` or serialized size bounds such as `1 + k.ghost_serialize().len() + v.ghost_serialize().len() <= usize::MAX` for concrete composite messages, or any proof needing bounds involving `ghost_serialize().len()`/serialized component lengths where direct arithmetic assertions keep failing.

**Obstacle:** Isolated constant inequalities like `1 + 8 + (8 + 1024) <= usize::MAX` do not connect to the actual `ghost_serialize().len()` expressions, and the verifier does not know exact serialization lengths of specific terms from a single direct inequality assertion.

**Mechanism:** Establish each component's serialization length bound explicitly through available marshalable/fixed-size or helper lemmas, instantiate those lemmas on concrete values, sum the component bounds, and compose a complete arithmetic chain from the actual serialized length sum to the target bound.

**Procedure:**
1. Write the exact target bound in terms of the variables' serialization lengths, e.g. `1 + k.ghost_serialize().len() + v.ghost_serialize().len() <= usize::MAX`.
2. Identify each component whose serialized length contributes to the bound.
3. Prove or locate a length lemma for each component type, then assert or apply that bound for each serialized component length using available marshalable or fixed-size lemmas.
4. Combine those component bounds explicitly to derive the total sum bound, composing the arithmetic chain into one complete inequality.
5. Use the derived bound directly to discharge the `is_marshalable()` or size-bound precondition; avoid relying on one direct assertion such as `1 + 8 + (8 + 1024) <= usize::MAX` unless the component length facts are already known.

**Why:** Verus can follow an arithmetic chain grounded in actual length expressions, but cannot connect isolated numeric constants to symbolic serialized lengths; structured component lemmas make the length facts visible to the verifier and avoid endless patching of direct arithmetic claims.

**Check:** The final arithmetic assertion references the same variables as the precondition, not only literal constants; after component lemmas are applied, the failure mode of unresolved serialization-length assertions is removed and a future run should close the arithmetic bound.

**Avoid or stop:**
- Do not rely on isolated numeric examples; they may be true but irrelevant to the goal.
- If component length facts are not available, derive them first.
- Do not present this as verifier-confirmed success; it is a suggested recovery from a failed trajectory.
- Do not use if the required component length definitions are inaccessible or closed.

<a id="verus-global-065"></a>

## verus_global_065 — Discharge derived is_marshalable with exact macro lemma

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Calling methods like `send_single_cmessage` requires `msg.is_marshalable()` for a derived enum/message type; sub-component or `message_marshallable()` facts are insufficient.

**Obstacle:** The proof kept failing on the `is_marshalable()` precondition even after proving `message_marshallable()` and component marshallability.

**Mechanism:** Invoke the exact lemma generated by the `marshalable!` or derive macro for the whole message type, or explicitly expand the derived `is_marshalable` condition for the constructor. Treat `message_marshallable()` and `is_marshalable()` as distinct.

**Procedure:**
1. Identify the constructor of the message value, such as `CMessage::Delegate`.
2. Find the whole-type lemma generated by `derive_marshalable_for_enum` or the relevant macro expansion for that constructor.
3. Call that lemma on the concrete message value to derive `out_m.is_marshalable()`.
4. Do not expect a sub-component lemma such as `lemma_is_marshalable_CKeyHashMap` or `message_marshallable()` to directly close the distinct `is_marshalable` obligation.

**Why:** Derived `Marshalable` preconditions are discharged by their own macro-generated lemmas; using a similar-sounding property leaves a gap.

**Check:** The generated lemma's conclusion exactly matches the required `is_marshalable()` predicate.

**Avoid or stop:**
- Do not confuse `is_marshalable()` with `message_marshallable()` or component-level marshallable properties.
- If the exact macro lemma is unavailable, expand the macro condition explicitly and prove each field, then close the whole-type condition.

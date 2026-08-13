---
name: verus-proof-repair
description: Root playbook for using this Verus proof skill directory. It explains how to ground a failing Verus obligation, classify the missing proof bridge, choose the smallest mechanism from M, apply it once, run Verus, interpret the changed diagnostic, and decide whether to open a reference or return to M. It is usable before opening any reference and contains no per-lemma details.
---

# Verus Proof Grounding, Obstacle Classification, and Minimal Mechanism Selection

Use the broadly applicable procedures below before opening a reference.

## Core procedures

### Ground the exact obligation

**When:** Before any proof edit, especially after a failed run or after a reference mechanism has been applied.

1. Run Verus on the current target file and capture the complete diagnostic, not a summary.
2. Identify the failing function, loop, return point, or assert; quote the exact predicate or precondition that remains unsupported.
3. Determine whether the failure is a missing contract/invariant, an unproven equality or implication, a trigger/instantiation problem, or an environment/syntax failure.
4. Do not edit until the exact stuck term is known.

**Check:** One can state the exact blocked conjunct or Verus error location before choosing a mechanism.

### Classify the missing bridge

**When:** After grounding, when deciding whether a fact can be handled from root knowledge or needs a reference.

1. Classify as one of: ordering/gap bridge; finite-set/membership/cardinality bridge; recursive sequence/fold recurrence; pointwise or extensional equality closure; quantifier trigger/instantiation; opaque/closed definition boundary; ghost/spec-view mismatch; loop invariant/termination gap; branch/return postcondition gap; structural wrapper/product decomposition; serialization/marshalability gap; missing lemma/spec inventory gap; syntax/macro environment issue; or verification-process hygiene.
2. Prefer root-level mechanisms only for the common classification and local proof hygiene steps.
3. If the missing bridge is lower-frequency and concrete, choose the single reference matching that classification.

**Check:** The classification names the mechanism family and predicts why the solver cannot close the goal.

### Choose the smallest mechanism and apply one change

**When:** Before opening a reference or after returning from one.

1. From M, use only the smallest structural or assertion change that can affect the exact blocked conjunct: strengthen one invariant, assert one equality, instantiate one lemma, split one case, or expose one definition/trigger.
2. Do not batch multiple independent proof mechanisms in the same edit when verifying a new mechanism.
3. Preserve existing requires/ensures and executable semantics; add proof scaffolding, not behavioral changes.
4. If the chosen mechanism is in a reference, apply one mechanism from that reference and return to M after one Verus run.

**Check:** The edit affects the stuck obligation directly and is small enough to attribute the resulting diagnostic change to it.

### Run Verus and interpret the changed diagnostic

**When:** After every mechanism application.

1. Run Verus on the intended target and read the full output, not only the first error.
2. Compare the new diagnostic with the previous one: did the failure move to a later conjunct, change to a different error kind, or disappear entirely?
3. If the diagnostic is unchanged, treat the mechanism as ineffective and reclassify rather than repeating the same step.
4. If the diagnostic changed, the obstacle has shifted; return to grounding and classification before applying the next mechanism.

**Check:** The next action is determined by the delta between the previous and current Verus diagnostic.

### Use a reference only for a concrete lower-frequency obstacle

**When:** After M's root procedures are exhausted or the classification indicates a specialized mechanism.

1. Open exactly one reference whose consult_when matches the concrete obstacle.
2. Use its guidance to select a single mechanism; do not hop to another reference until the diagnostic is re-read.
3. Apply one mechanism, run Verus, and then return to M to reclassify the new diagnostic.
4. If no reference exactly matches, stop and report the unresolved classification instead of opening several references speculatively.

**Check:** At most one reference is opened for the current obstacle, and the next step after the attempt is a fresh root-level reclassification.

### Decide when to stop consulting a reference or stop proof changes

**When:** A reference mechanism was applied, or the proof is blocked by absent definitions, missing lemmas/spec axioms, forbidden assumptions, macro unavailability, or repeated failures of the same shape.

1. If the same reference mechanism has been tried once and the diagnostic is unchanged, stop repeating that reference mechanism.
2. Check whether the needed fact is actually present in the current contracts, trait bounds, or existing lemmas.
3. If a required lemma/spec property is absent and cannot be proved without forbidden assumptions, report the specification gap.
4. If the file is uncompileable due to environment/macro/syntax issues, repair that before proof work.
5. Do not add assume/axiom/external_body/unimplemented placeholders to close a proof gap.

**Check:** No repeated failed mechanism is left in place, and no unsound artifact is used to convert an unproven obligation into apparent success.

## Progressive reference consultation

1. Load M and ground the verifier failure first.
2. Apply root-level proof hygiene and classification before consulting a reference.
3. Open at most one reference when the obstacle is a specialized lower-frequency mechanism; do not preload all references.
4. Apply one mechanism from that reference and run Verus immediately.
5. Read the complete diagnostic and compare it with the previous run.
6. Return to M after every reference mechanism attempt; reclassify whether the failure moved, vanished, or is unchanged.
7. If the failure changed, select the next mechanism from M or the same/matching reference only after re-grounding.
8. If the failure did not change, stop consulting that reference and either reclassify or report a missing lemma/spec/environment gap.

## Safety and stopping rules

- Do not alter executable behavior or weaken existing requires/ensures contracts to make a proof pass.
- Do not use assume, admitted lemmas, external_body placeholders, unimplemented!, new axioms, or similar proof bypasses unless explicitly permitted by the task.
- Do not write proof work in a clone when the task requires the supplied target file; edit the target in place.
- Do not declare success from truncated or partial Verus output; require a complete 0-error run on the intended target.
- Do not rely on nonexistent or private library lemmas; verify existence, signature, and preconditions before invoking.
- Do not repeat failed reveal/broadcast/fuel tuning or repeated macro regex edits; stop and reclassify.
- Preserve verified lemmas and contracts; after cleanup, rerun Verus to confirm 0 errors remains true.

## Reference map

### [Ordering, Sortedness, Gap, and Range-Bound Proofs](references/ordering_sortedness_range_proofs.md)

**Consult when:** The stuck goal depends on custom comparator order properties, trichotomy/gap case splits, inclusive/exclusive range mismatches, consecutive sorted-key gaps, contiguous sorted-range induction, sortedness after one update/insertion, or transitive index-bound chains.

**Do not consult when:** The obstacle is only a pointwise/set extensionality or trigger problem, or the ordering facts are already sufficient and the remaining gap is loop/invariant or serialization-related.

- `verus_global_001` — Unlock user-defined comparator transitivity and trichotomy before ordered reasoning: A proof goal depends on a user-defined comparison relation or custom comparator and requires chaining strict inequalities or trichotomy, but the SMT solver cannot derive the order properties of that relation.
- `verus_global_002` — Trichotomy-driven case split for gap and adjacent order facts: A goal must prove an ordering relation or gap for an arbitrary intermediate key between two bounds, and the relation has disjoint alternatives beyond strict less-than, including equality and possibly an iterator-end sentinel.
- `verus_global_003` — Resolve inclusive/exclusive range mismatches by inspecting predicate definitions: The goal appears to require a property over an inclusive index or key range while an existing lemma covers an adjacent or exclusive range, creating an apparent off-by-one or boundary mismatch.
- `verus_global_004` — Prove consecutive sorted-key gaps via sorted-index order contradiction: A proof must establish that there is no key belonging to a strictly sorted finite key sequence strictly between two consecutive elements at indices i and i+1.
- `verus_global_005` — Inductively decompose contiguous sorted-key range proofs: A uniform property must be proved over a contiguous range of sorted keys, and a direct monolithic proof does not close or is too complex.
- `verus_global_006` — Prove sortedness after a single key update by index-case split: A sorted sequence has one element updated or replaced, and the goal is to re-establish sortedness for all pairs of indices.
- `verus_global_007` — Re-establish map-wide invariant after a single key insertion by old/new key split: A map is mutated by inserting one key, and the goal is a map-domain invariant over every key in the domain.
- `verus_global_008` — Encode transitive index-bound chains as one invariant: A proof relies on separate ordering facts of the form A <= B and B <= C, and a subsequent derived arithmetic or index comparison only follows when the chain is available as a compact transitive fact.
- `verus_global_009` — Recover GLB index ordering proof from failed unsupported assertions: A proof requires ordering between greatest-lower-bound indices derived from GLB specifications and sortedness, after prior attempts with assert-false or unfinished contradictions failed.
- `verus_global_010` — Bridge range-consistency statements with explicit witnesses instead of bare forall: A goal needs to show one range-consistency predicate over a wider key interval implies another, and previous attempts used assert-forall with high-level comments or simple references to gap and GLB lemmas without instantiating them.

### [Finite-Set Cardinality, Membership, and Equality Proofs](references/finite_set_membership_equality.md)

**Consult when:** The goal is set cardinality/finiteness, set equality or subset membership, sequence-to-set length, choose-based witness extraction, derived set operations, or membership transfer through sequence transformations.

**Do not consult when:** The goal is an ordering chain, loop invariant, or serialization segment, even if it mentions sequences; use those references instead.

- `verus_global_011` — Duplicate-free sequence-to-set cardinality by insert-length axiom: When proving `s.to_set().len() == s.len()` for a duplicate-free sequence `s`, or deriving cardinality changes after inserting a fresh element into a set.
- `verus_global_012` — Use fold-representation lemmas to prove derived set-operation finiteness: Proving finiteness of a high-level set operation such as `s.map(f)` when only lemmas about `map_fold` are available and the proof body is empty.
- `verus_global_013` — Preserve finiteness through insert in recursive set-fold proofs: Proving `map_fold(s, f).finite()` by induction on a recursive set fold whose step inserts into a known-finite set.
- `verus_global_014` — Set function equality by empty/nonempty case split and induction: Proving equality between a recursive set function and a high-level operation like `s.map(f)`, with induction on a smaller set.
- `verus_global_015` — Set equality by choose-based witness extraction inside membership forall: Proving `setA == setB` or `setA =~= setB` for compound finite-set expressions, especially when one side's membership condition is existential and built-in macros such as `assert_sets_equal!` fail or Verus does not automatically apply set extensionality.
- `verus_global_016` — Prove subset relations involving derived sets by explicit forall, guarded implications, and existential witness reuse: Proving `s.subset_of(flatten_sets(sets))` or similar subset relationships involving a derived set, where automatic unfolding is insufficient.
- `verus_global_017` — Relate sequence-derived sets by index witnesses and case splits: Proving membership or equality between sequence-derived sets across tail decomposition or push, using explicit sequence index witnesses.

### [Recursive Sequence and Fold Induction](references/recursive_sequence_fold_induction.md)

**Consult when:** The proof is stuck on fold_left/prefix-last decomposition, elementwise lifting through folds, sequence-filter recurrences, push/mutation subrange-fold closure, or index-dependent recursive helpers over sequences.

**Do not consult when:** The goal only needs set equality, structural wrapper decomposition, or post-loop universal closure without a recursive recurrence.

- `verus_global_018` — Fold-left sequence equality by recursion-aware length induction and prefix/last decomposition: Verus must prove an equality or equivalence involving Seq::fold_left over a whole sequence, a prefix/last decomposition, or two elementwise-equivalent sequences; the necessary connection is not discharged by SMT after unfolding or solver tuning.
- `verus_global_019` — Lift elementwise sequence equivalence through fold using an existing fold equivalence lemma: A postcondition or proof goal has already established elementwise equivalence between two sequence arguments and must use it to prove equality of the results of a fold or accumulation operation.
- `verus_global_020` — Isolate missing sequence-filter recurrences into atomic test lemmas: A proof about Seq::filter is stuck on a recursive head/tail or singleton/empty base-case equality such as s.filter(pred) == s.skip(1).filter(pred) or seq![x].filter(pred), despite repeated reasoning, broadcast axioms, fuel changes, or manual assertions.
- `verus_global_021` — Use ghost snapshots and subrange extension equalities for push/mutation spec-view closure: After an executable mutation such as Vec::push, or a step that mutates a buffer, vector, or `self`, a proof must re-establish equality of an abstract ghost view, a subrange, or a folded serialization with a specification-side sequence, or preserve old-state preservation and new-state/suffix equality against a spec accumulator.
- `verus_global_022` — Prove index-dependent list or sequence properties by isolated helper induction on the index: A target lemma must establish a property of list[k] or seq[k] parameterized by index k, given a sequentiality or order relation and a base element precondition.

### [Pointwise, Universal, and Extensional Sequence/Set Closure](references/pointwise_sequence_set_equality_closure.md)

**Consult when:** A universal ensures, set/sequence equality, singleton contents, elementwise lemma application, or post-loop full-range equality must be closed by explicit forall/pointwise reasoning and extensionality.

**Do not consult when:** The missing fact is a trigger selection issue, a recursive fold recurrence, or a branch/return postcondition with no elementwise equality.

- `verus_global_023` — Discharge universal ensures and arbitrary-value postconditions with `assert forall`: `ensures forall|x: T| P(x)` or a postcondition involving an underspecified returned value whose concrete identity is unavailable in the ensures.
- `verus_global_024` — Set equality by explicit membership forall and extensionality: Set equality goal `A == B` where both sides are sets or sequence-derived sets and membership can be stated with `contains`.
- `verus_global_025` — Ground singleton sequence contents by index and length facts: Reasoning about a singleton sequence `seq![x]` or a sequence known to have one element, especially when connecting `to_set()` and singleton set membership.
- `verus_global_026` — Elementwise lemma application for collection-level predicates: Collection-level property over sequences or views where the element type exposes a lemma that proves the needed per-element fact.
- `verus_global_027` — Post-loop universal and sequence-equality closure from loop invariants: A loop invariant already maintains a per-index, pairwise, or elementwise property, but the postcondition requires the same property for all indices after the loop, possibly as sequence or set extensional equality; in the sequence-equality variant, two sequences have equal length and the loop invariant maintains equality for every index up to a counter that ends at that length.
- `verus_global_028` — Sequence equality by length, pointwise equality, and `=~=`: Direct sequence equality `seq1 == seq2` for any sequence operations, where length equality and pointwise element equality can be asserted.

### [Quantifier Trigger Selection and Concrete Instantiation](references/quantifier_trigger_selection.md)

**Consult when:** Verus reports missing/no-selected-trigger warnings, automatic trigger selection is preferred, or a quantified premise needs a concrete index-element assertion to instantiate.

**Do not consult when:** The quantifier body itself is unproved due to missing recursive lemmas or structural decomposition; trigger annotation will not close those gaps.

- `verus_global_029` — Explicitly annotate a forall predicate with #[trigger] to suppress missing trigger warnings: Verus emits a missing or no-selected-trigger warning for a `forall` assertion, and the predicate or implication antecedent that should drive quantifier instantiation is textually identifiable.
- `verus_global_030` — Insert #![auto] on forall quantifiers to let Verus choose triggers: Verus suggests a trigger annotation for a `forall` expression, warns of missing triggers, or fails to instantiate an elementwise or range `forall` where automatic trigger selection is preferable.
- `verus_global_031` — Assert a concrete index-element equality to instantiate a quantified premise with an existing equality trigger: A quantified premise contains an existing `#[trigger]` equality such as `g(i, a) == f(a)`, and the proof goal requires the same equality for a concrete index and concrete element from the current collection or map.

### [Closed and Opaque Definition Boundaries](references/closed_definitions_and_broadcast_boundaries.md)

**Consult when:** A proof requires revealing an opaque definition with compute_only, or reveal/broadcast attempts are failing because a term is hidden behind a closed/axiomatic definition.

**Do not consult when:** The function is obviously open and the issue is a missing recurrence or insufficient invariant; revealing definitions will not help.

- `verus_global_032` — Use `assert ... by(compute_only)` to reveal opaque definitions early: When a proof is stuck because Verus is not automatically unfolding an opaque function whose body is needed to align an assertion or induction scheme.
- `verus_global_033` — Stop reveal/broadcast attempts when closed or axiomatic definitions hide triggers: When a proof needs to connect a goal term expressed through a closed definition to a lemma or broadcast trigger, or when it needs the internal definition or equational behavior of a spec function or axiom, especially when reveal, reveal_with_fuel, or broadcast use is being attempted.

### [Ghost Snapshots, Spec Views, and Concrete-to-Abstract Equality](references/ghost_snapshots_spec_views.md)

**Consult when:** Proof blocks need @-views, stable let ghost snapshots, replacement of arbitrary ghost placeholders, Ghost return placement, or chains from concrete fields/views to abstract specs.

**Do not consult when:** The main issue is loop invariant design or recursive sequence recurrence rather than concrete/ghost typing and view chain scaffolding.

- `verus_global_034` — Bind inline results and ghosts to named lets for stable triggers and ensures: An assertion, quantifier, or later proof block must refer to an inline function result, a sequence expression, or a ghost snapshot, but the term is unnamed or proof-block scoped.
- `verus_global_035` — Expose spec-view sequence values with @ for proof indexing and length reasoning: A proof or ghost block must index or reason about lengths and elements of a concrete collection, or it currently uses executable indexing inside `proof`.
- `verus_global_036` — Chain concrete fields, abstract snapshots, and spec-view equalities to satisfy view postconditions: A postcondition equates a concrete value or structure with an abstract spec function over a view; the relation is not direct, and invariants may recur over a collection.
- `verus_global_037` — Replace arbitrary ghost placeholders with concrete values and bridge to specs in proof blocks: A ghost variable or return value is initialized with `arbitrary()` and postconditions about it are unprovable, or an already computed concrete result needs to be connected to an abstract specification.
- `verus_global_038` — Place Ghost returns outside proof blocks: A function body declares a ghost value and uses proof-block assertions to justify it, then must return that ghost value.
- `verus_global_039` — Assume direct precondition consequences to expose view-to-value equality: A proof must exploit an equality directly implied by a precondition such as `view_equal` before proving method-call equalities or value equality.

### [Loop Invariant Design, Break Provenance, and Termination Measures](references/loop_invariants_and_termination.md)

**Consult when:** A loop reports out-of-bounds or length facts, post-loop universals require a processed-prefix invariant, early break provenance is needed, or a while/recursive proof function needs a decreases measure.

**Do not consult when:** The loop body is fine and the only failure is a set equality or serialization detail after the loop; close those with their own references.

- `verus_global_040` — Carry collection length and cursor bounds as loop invariants for safe indexed mutation: A Verus loop uses an integer cursor to index or remove from a Vec or slice, and Verus reports possible out-of-bounds or cannot prove the current collection length.
- `verus_global_041` — Quantified processed-prefix invariants for elementwise and monotonic properties: A loop scans indices from a lower bound and the postcondition needs a universal fact over all visited or processed elements, such as element equality, view equality, sortedness, or value agreement.
- `verus_global_042` — Preserve early-exit provenance with ghost state and biconditional loop invariants: A loop contains a conditional break, and a post-loop proof obligation depends on whether or why the loop exited before exhausting the range.
- `verus_global_043` — Prioritize a loop invariant that directly implies the primary postcondition over auxiliary fixes: A loop is written or being patched, but the main postcondition remains unproven after the loop, while work drifts toward body assertions, helper lemmas, arithmetic bounds, or validity side facts.
- `verus_global_044` — Add a nonnegative bound-minus-counter decreases measure to while loops: Verus while loops with a monotonic counter moving toward a known upper or lower bound when the verifier reports a missing decreases clause or termination failure. For the upper-bound form, includes inclusive upper-bound loops with condition `counter <= upper_bound` where the invariant allows the counter to reach `upper_bound + 1` before/at exit, making a naive `upper_bound - counter` measure negative.
- `verus_global_045` — Use an explicit sequence-length decreases clause for recursive proof functions and lemmas: Recursive Verus proof functions or lemmas that induct over a sequence or make a recursive call on a shorter sequence, and produce a cannot-prove-termination or must-have-a-decreases error.
- `verus_global_046` — Induct over finite sets using decreases set length and element removal: Recursive proof functions or lemmas over finite sets that require induction on set size, or where Verus reports termination failure and the induction step needs a smaller set.

### [Branch, Exit, and Return-Point Postcondition Closure](references/branch_return_postcondition_closure.md)

**Consult when:** The top-level ensures remains unproved at a specific return path, an early false return refutes a global predicate, a no-field constructor branch reduces trivially, or an Option-valued postcondition must be split before unwrap.

**Do not consult when:** The proof needs a structural component lemma or loop invariant; return-site assertions are secondary.

- `verus_global_047` — Close top-level ensures at each return with branch-specific assertions: Function postcondition is a named predicate or disjunction depending on branch state, and branch-specific facts have already been proved but the top-level ensures remains unproved at return.
- `verus_global_048` — Discharge early false return by asserting concrete counterexample and negated global postcondition: Function has an early `return false` when a local counterexample violates an aggregate postcondition, and the ensures clause is a global predicate that must be shown not to hold.
- `verus_global_049` — Leave no-field constructor branches empty when postconditions reduce to the same constant: Case-analysis branch matches a no-field constructor on both sides, and postcondition equalities reduce to identical constructor constants.
- `verus_global_050` — Split Option-valued postcondition into Some and None branches before unwrapping: External-body or function ensures refers to an Option value through unwrap and must be defined for both Some and None cases.

### [Structural Decomposition for Option, Struct, Enum, and Composite Properties](references/structural_component_decomposition.md)

**Consult when:** A wrapper/sum type needs constructor case split with inner lemmas, a product/struct property delegates to components, bidirectional structural equivalence is needed, or a combined postcondition must be decomposed field-wise.

**Do not consult when:** The issue is specifically serialization length/tag decomposition or fixed-width byte lemmas; use the serialization reference unless the only obstacle is wrapper/product structure.

- `verus_global_051` — Option-like wrapper/sum case split with inner component lemma and tag contradiction: A wrapper or tagged-sum type with two constructors, such as Option<T>, defines or serializes a structural predicate, equality, symmetry, prefix, or injectivity property by case analysis over the constructors and reduces to an inner component property in the matching constructor arm. The wrapper-level goal may involve equality, symmetry, serialization equality, prefix non-membership, or injection from full serializations, and its proof depends on the inner type T.
- `verus_global_052` — Composite product type component-wise lemma delegation: A composite product type such as a tuple or multi-field struct defines a structural predicate, equality, serialization relation, or view relation component-wise. A lemma or property is already known for each component type, and the goal is to prove the same property for the composite type by delegating to those component lemmas.
- `verus_global_053` — Bidirectional structural equivalence by explicit implication splitting: A structural equivalence relation or predicate is defined by a structural size fact plus an elementwise or componentwise condition. The goal is to prove symmetry of the predicate, typically as a boolean equality between P(self, other) and P(other, self).
- `verus_global_054` — Decompose combined abstract-state and invariant postconditions into sequential field-wise blocks: A function or constructor postcondition combines an abstract state specification predicate and a structural invariant over a concrete state type with an abstract view projection. The proof must establish argument-derived facts, invariant satisfaction, and field-wise equality with the abstract specification.
- `verus_global_055` — Establish structural well-formedness via empty auxiliary collections and per-element predicate: A result or state struct has auxiliary collection fields and an active collection field. A structural well-formedness predicate is satisfied by setting the auxiliary collections to empty and proving a per-element variant predicate over the active collection.

### [Serialization, Marshalability, Prefix, and Size-Bound Proofs](references/serialization_marshalability_proofs.md)

**Consult when:** The goal involves fixed-width integer roundtrips, wrapper serialization delegation, tag/prefix/suffix segment equalities, concatenated prefix component equalities, vector injectivity by element induction, component prefix inequality, marshalable size bounds, or derived is_marshalable macro lemmas.

**Do not consult when:** The goal is only generic set/sequence equality, trigger selection, or structural wrapper decomposition with no byte-level/tag reasoning.

- `verus_global_056` — Fixed-width integer serialization roundtrip equality and contradiction: Proof goal involves `spec_u64_to_le_bytes` / `spec_u64_from_le_bytes` or an analogous fixed-width integer serializer, and requires equality or contradiction from serialized bytes.
- `verus_global_057` — Wrapper serialization proof by delegating to the inner type: A wrapper type's `ghost_serialize` or serialization lemma is defined by converting to an inner type and reusing that inner type's serialization, such as `usize` cast to `u64`.
- `verus_global_058` — Same views serialize the same via primitive value equality: Proving `lemma_same_views_serialize_the_same` for a primitive or view-equal type where `view_equal` implies actual equality.
- `verus_global_059` — Serialize postcondition by subrange segment decomposition: A serialization function appends a tag byte and a recursively serialized value; the proof obligation is that the final data subrange equals the concatenation.
- `verus_global_060` — Concatenated prefix equality via fixed-width length and element-wise indexing: Given equality of concatenated serializations `a + b == c + d` and a known equal or fixed prefix length, prove component equality `a == c` and `b == d`.
- `verus_global_061` — Recover vector injectivity with concrete element induction: Vector serialization injectivity when generic fold-left sequence reasoning is failing; the proof may be reduced to induction over vector length or element index.
- `verus_global_062` — Lift component prefix inequality to whole concatenated serialization: Tuple or composite serialization is `s0 + s1`; need to prove whole serialization is not a prefix when a component is not a prefix.
- `verus_global_063` — Avoid unproven component-length contradiction in tuple serialize injectivity: Trying to prove component serialized length equality when concatenated serializations are equal, such as tuple serialize injectivity.
- `verus_global_064` — Marshalable size bounds from per-component serialization length arithmetic chain: Proving `is_marshalable()` or serialized size bounds such as `1 + k.ghost_serialize().len() + v.ghost_serialize().len() <= usize::MAX` for concrete composite messages, or any proof needing bounds involving `ghost_serialize().len()`/serialized component lengths where direct arithmetic assertions keep failing.
- `verus_global_065` — Discharge derived is_marshalable with exact macro lemma: Calling methods like `send_single_cmessage` requires `msg.is_marshalable()` for a derived enum/message type; sub-component or `message_marshallable()` facts are insufficient.

### [Lemma Reuse, Helper Decomposition, and Library/Spec Inventory](references/lemma_reuse_and_spec_inventory.md)

**Consult when:** A proof should reuse existing helper/trait/source lemmas, needs a helper extraction, lacks a fold accumulator lemma, or is failing because a named/spec/trait property may be absent or private.

**Do not consult when:** The exact lemma exists and is available but the immediate issue is trigger selection, loop invariant, or syntax/environment errors.

- `verus_global_066` — Discharge top-level postconditions by invoking helper/lemma postconditions and asserting only necessary subgoals: A top-level ensures/postcondition is a conjunction or follows from properties already proved by implementation helpers or named lemmas; the proof state contains those helper postcondition facts but the verifier does not automatically combine them into the target.
- `verus_global_067` — Let a stronger precondition drive direct lemma instantiation without case splits: The current function precondition already guarantees a superset of what a helper lemma requires, such as a closed range where the lemma needs a half-open range.
- `verus_global_068` — Replace external_body lemmas with explicit proof bodies using assertion chains: A lemma is declared with #[verifier::external_body] and must become self-contained rather than relying on an external assumption.
- `verus_global_069` — Refactor a stalled complex postcondition into smaller helper lemmas: A direct proof body becomes littered with unprovable assertions or nested case splits, especially for complex serialization/prefix properties.
- `verus_global_070` — Introduce a helper lemma to unpack fold_left accumulator semantics: A property depends on the result of a fold_left-based function and needs to relate the full accumulated value to the prefix result plus the tail element.
- `verus_global_071` — Inventory and validate source/vstd lemma availability before ad-hoc proof: A proof appears to need a reusable property, or intends to rely on a named source/vstd/seq_lib lemma; the source file, trait bounds, project, exact lemma name, module path, privacy, or preconditions may not yet have been verified.
- `verus_global_072` — Recognize missing trait or spec properties before repeatedly restructuring a proof: A proof depends on a property that is not supplied by the current trait or spec, and syntactic restructuring cannot close the logical gap.
- `verus_global_073` — Use existing substructure, trait-bound, and structural lemmas before low-level sequence reasoning: A composite or sequence/serialization proof is stalling on manual low-level index, subrange, or prefix assertions while relevant lemmas exist on trait bounds or in the file.

### [Verus Syntax, Macro, Crate, and Type-Environment Repairs](references/syntax_macro_crate_environment.md)

**Consult when:** Verus fails to compile or emits syntax/deprecation/type-inference/trait-contract/macro-availability errors before the intended proof gap is reachable.

**Do not consult when:** The file already compiles and the remaining failure is a logical proof obligation, not an environment or syntax error.

- `verus_global_074` — Replace deprecated Verus `is_None()` syntax with modern `is None` pattern matching: Verus verification succeeds or nearly succeeds, but emits a deprecation warning for legacy `is_None()` on an Option value.
- `verus_global_075` — Rename quoted quantifier-bound variables to Rust 2021-compatible identifiers: A Verus proof block uses a quantifier closure such as `forall|s'| ...` or `exists|s'| ...` and compilation fails under Rust 2021 because of single quotes in the closure parameter name.
- `verus_global_076` — Resolve Verus type-inference failures for ambiguous generic constructors and sequence literals with explicit annotations: Verus reports cannot-infer-type errors for generic proof/spec constructors such as `Map::empty()`, `Seq::empty()`, or untyped integer sequence literals such as `seq![0]` in ghost/proof code.
- `verus_global_077` — Remove duplicated trait requires/ensures clauses from implementation methods: A Verus `exec fn` implements a trait method and repeats the trait's `requires`/`ensures` contract in the implementation, causing a contract redeclaration error.
- `verus_global_078` — Avoid introducing invalid nested proof constructs during proof search: While searching for a proof, edits introduce unsupported or invalid Verus constructs such as a nested `proof fn` inside another function or invalid use of `vstd::pervasive::unreached()` in a `proof fn` context.
- `verus_global_079` — Repair Verus macro/crate environment, or manually expand macros with validation: A Verus file fails to compile because macros reference `::builtin_macros::verus!` or an unavailable procedural macro, especially when the file is invoked standalone rather than inside a minimal Cargo project; if the macro environment cannot be repaired, the file must be made self-contained by expanding macros to concrete Verus items.
- `verus_global_080` — Avoid regex-based Verus macro expansion for nested multiline braces; prefer direct edits with incremental verification: An agent considers or uses a regex/script to remove or expand multi-line `macro_rules!` Verus macros with deeply nested brace-heavy bodies.

### [Verification Process, Soundness, and Proof-Maintenance Hygiene](references/verification_workflow_soundness.md)

**Consult when:** The task requires disciplined in-place editing, complete Verus feedback, empty-body checks, helper independence, forbidden-assumption audits, smallest-obligation isolation, or post-verification cleanup.

**Do not consult when:** The proof is already hygienic and only a specific mathematical bridge is missing; use the corresponding mechanism reference.

- `verus_global_081` — Edit the supplied target file in place for proof-annotation tasks: Task names an existing source file for proof annotations; the proof has not yet been applied to that exact file.
- `verus_global_082` — Gate proof construction on complete Verus output before and after edits: Before editing a proof target, after each non-trivial proof edit or transformation, and before declaring completion.
- `verus_global_083` — Check whether an empty proof body already satisfies a definitional obligation: When a proof function is empty or minimal and the postcondition may reduce directly to a definitional equality.
- `verus_global_084` — Complete helper lemma proofs independently before depending on them: When introducing or reusing a helper lemma whose body is empty, comments-only, recursive without closing the induction, or not independently verified.
- `verus_global_085` — Audit proof dependencies, reject forbidden assumptions, and report unsolvable specification gaps: When a proof uses or plans to use `external_body`, `unimplemented!()`, `assume`, `admit`, new axiom functions, or trait methods with opaque or external concrete bodies and task rules forbid them, or when repeated compliant proof attempts cannot close an obligation and a new axiom or unsound assumption appears to be the only route.
- `verus_global_086` — Isolate the smallest failing obligation and decompose or pivot when stuck: When a postcondition or invariant remains unproved after multiple edits, or when a proof block is large and the verifier failure is not yet isolated.
- `verus_global_087` — Remove redundant assertions after successful verification: After a proof verifies successfully and contains extra manual assertions that duplicate facts already established by existing lemma calls.
- `verus_global_088` — Write a complete proof in one self-contained edit when the structure is clear: When the required proof structure is already clear from the definitions and a single complete annotation is likely to verify immediately.

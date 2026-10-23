# old_prose: ten card bodies

Exact card content from the evaluated bundle. The actor reads these on demand.

## card-002

**Trigger:** The proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment.
**Action:** Establish set equality through pointwise membership equivalence. For the forward direction, derive membership in the image union from membership in either image using union and image definitions. For the reverse direction, when image membership is assumed on one side, introduce a chosen witness satisfying the corresponding source membership and mapping relation; prove the witness belongs to the union; then derive the union image membership and obtain the contradiction. If the verifier warns about low-confidence triggers for the quantified equivalence, accept the automatic trigger or annotate the equivalence to give the solver reliable membership triggers.
**Why:** The reverse direction requires exposing the existential witness because merely asserting union-image membership does not give the solver enough information. The chosen witness connects the image definition to union membership. Trigger annotation can suppress a warning after the logical witness step succeeds, but the success depends on that witness.
**Validate:** Run the verifier after adding the witness step and confirm zero errors; then run the proof-safety comparison. Confirm no assumptions or specification changes were introduced.
**Avoid when:** A directly applicable library lemma proves the same obligation and its premises hold, because manual witness reasoning is then avoidable. Also avoid assuming after a successful proof that the trigger annotation alone was responsible for discharging the obligation; it may only have suppressed a warning.

---

## card-017

**Trigger:** A proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure.

**Action:** Use induction on the cardinality of the finite input set. In the zero-cardinality case, show the folded result equals the empty set, so it is finite. In the nonzero-cardinality case, choose an element, assert that removing it strictly lowers the cardinality, recursively prove finiteness for the result over the remaining set, and assert that the full fold equals the recursive result with the image of the chosen element inserted. Conclude finiteness through the fact that inserting into a finite set preserves finiteness. Either add a recursive proof helper and call it from the required function, or if allowed add the decreasing clause and reason directly inside the required function.

**Why:** The recursive equality mirrors the recursive definition of the fold, so the full result is exposed as an insert over a smaller fold. Induction on a strictly decreasing cardinality gives termination and transfers the finiteness property step by step.

**Validate:** Rerun Verus until every function verifies with no errors, then run the proof-safety comparison and expect a zero exit and no differences.

**Avoid when:** The folding operator does not have a decreasing cardinality argument, or the empty and nonempty unfoldings do not produce the equality needed to transfer finiteness.

---

## card-022

**Trigger:** Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions. Concrete fold-bound and append-length obligations continue to fail even after those generic lemmas are invoked.

**Action:** Introduce specialized recursive lemmas over the concrete element type. In the empty case, unfold the fold with enough fuel and prove the zero or empty result. In the nonempty case, remove the final element, establish the elementwise facts for the shortened sequence, call the lemma on the remainder, unfold the fold again, and add the final element's contribution to the bound. Include preconditions that every element is well-formed for serialization and that each element satisfies the chosen numeric bound.

**Why:** The concrete fold expression matches the specialized lemma's conclusion exactly, whereas the higher-order lemma retains an abstract function argument that the solver does not rewrite into the concrete folding function.

**Validate:** The previously failing concrete fold-bound and append-length assertions discharge after replacement. Verus reports no errors and the proof-only safety comparison passes.

**Avoid when:** The generic lemma already instantiates correctly, or the recursive structure does not provide a decreasing well-founded measure.

---

## card-029

**Trigger:** A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier. **Action:** Instantiate the helper that moves always across the universal using two pointwise predicate families that differ only in whether the always wraps the implication. For each index, discharge the helper precondition by reducing both entailment directions to self-entailment of the same always predicate; a local reflexivity assertion is sufficient. Then instantiate the helper that commutes a plain implication through the universal quantifier. Chain the resulting equalities under congruence of always to close the target. **Why:** The two helper postconditions rewrite the left side into the right side in two compatible steps. The precondition is definitional reflexivity after the always operation is applied to the same underlying predicate, so it does not require a new lemma. **Validate:** Rerun Verus and expect verification with zero proof errors; then run the behavior-preservation checker and confirm it exits successfully. In the observed traces this helper chain closed the postcondition, while a missing local proof block produced a syntax error and was fixed by adding a local reflexivity assertion. **Avoid when:** Do not attempt to unfold all temporal definitions globally or introduce a new universal temporal rule. Do not skip the precondition assertion for the always-moving helper, because its external body still requires that premise to be discharged.

---

## card-037

**Trigger:** A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically.
**Action:** Introduce a small proof-only helper that takes the whole-sequence property and an in-bounds index and concludes the element property, then call that helper in the loop body. Use the concrete indexed term at the call site so the quantifier trigger can match.
**Why:** A bounded forall often requires an explicit instantiation step; a lemma localizes that step and keeps the loop body legible.
**Validate:** Rerun Verus; the previously failing element assertion or call precondition should become provable.
**Avoid when:** The element property is not actually derivable from the whole-sequence assumption under the available bounds, or the index is not guaranteed to be in range.

---

## card-058

**Trigger:** A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed. **Action:** Before using the premise at a concrete execution, assert the full implication-form satisfaction for that execution, not just the conclusion. Then apply the implication with the antecedent and conclude the right-hand side. This uses the existing universal hypothesis rather than adding any new trusted fact. **Why:** An entailment expands to a universal quantifier over executions, and SMT instantiation often needs the surface form of the implication applied to the chosen execution. **Validate:** Re-run Verus; the previously failing assertion should be discharged and the final target should close. **Avoid when:** The premise is not an entailment or validity over the same execution type, or the selected implication term does not match the premise's syntactic form; use a helper lemma or a different unfolding in that case.

---

## card-060

**Trigger:** Verus compile errors say a struct field is not a method when a stored spec function is applied directly to an argument in a proof. **Action:** Rewrite each occurrence so the field projection is parenthesized first and then applied to the index argument. After fixing parsing, if Verus reports a missing trigger for the universal equality, add explicit trigger annotations to both sides of the equality. **Why:** The field stores a function value rather than a method, so the parser needs the projection to be treated as a callable value. The explicit trigger then lets the pointwise equality quantifier instantiate at arbitrary indices so the execution equality lemma can be applied. **Validate:** Re-run Verus; compile errors should vanish. If a subsequent trigger error appears, adding the explicit trigger should enable verification, and the final proof should pass with all proof functions verified and the safety comparison clean. **Avoid when:** The field is not a function-valued field, or the equality can be proved by another supplied lemma without pointwise expansion; fixing syntax does not replace a missing logical fact.

---

## card-062

**Trigger:** Verus reports an empty or incomplete proof body for a temporal stability postcondition, and the target predicate is a finite conjunction of always-lifted state predicates. **Action:** Inspect the local temporal rule definitions and reuse the existing stability and conjunction-combination machinery, or the helper macro already present in the file. Apply it to each lifted state predicate in the same left-to-right order as the target predicate is constructed, rather than unfolding the temporal definitions by hand. **Why:** The supplied rules express exactly the two logical facts needed: every always predicate is stable, and stable predicates are closed under binary conjunction. Using them in the same order lets Verus connect the proof steps to the target's left-associated structure. **Validate:** Re-run Verus and confirm the postcondition is discharged with only pre-existing warnings, then run the proof-only safety comparison and inspect that only the proof body changed. **Avoid when:** The target is not a finite conjunction of always-lifted predicates, or the expected local stability and conjunction rules are absent or incompatible with the definitions.

---

## card-070

**Trigger:** A postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails.
**Action:** Prove the two semantic entailment directions separately. In the direction from the nested application to the single application, instantiate the outer and inner quantified statements at a concrete index and at zero. In the direction from the single application to the nested application, instantiate at the sum of two arbitrary indices. For each direction, prove equality of the underlying state or suffix objects pointwise at every index using simple arithmetic identities and the supplied pointwise-equality lemma, then invoke the supplied equality lemma for the spec-level objects.
**Why:** Equality of function-like specification objects is not derived automatically. The prover needs pointwise equality plus the supplied lemma that turns pointwise equality into object equality. The remaining mathematical work is arithmetic over indices and the existing object equality lemmas.
**Validate:** Run Verus after each entailment direction and ensure both verify before invoking the final equality lemma. Then run the proof-only safety comparison. Do not add new trusted bodies or weaken contracts; existing trusted declarations are background only.
**Avoid when:** Built-in extensional equality for those objects already suffices without manual pointwise evidence, or the arithmetic identity needed for the index shift is not available in scope.

---

## card-076

**Trigger:** A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases.
**Action:** Inline the local aliases back into the expanded suffix and predicate expressions used by the helper's preconditions. Then explicitly assert each quantified hypothesis the helper requires, using a conditional branch on the antecedent and asserting the exact quantified trigger term to force instantiation of the always fact.
**Why:** Local aliases can change the syntactic form that Verus uses to match quantifier triggers, so the propagated fact is not instantiated at the call site. Inlining restores the exact forms, and an explicit assertion of the trigger term invokes the universal fact.
**Validate:** Rerun Verus; the helper's quantified precondition should now be discharged and the surrounding proof should close. Confirm Lynette passes.
**Avoid when:** The aliases are not implicated in trigger matching or the necessary facts are not available as trusted quantified facts. Changing trigger selection is not required; accepting an existing automatic trigger to suppress a note is different from forcing instantiation.

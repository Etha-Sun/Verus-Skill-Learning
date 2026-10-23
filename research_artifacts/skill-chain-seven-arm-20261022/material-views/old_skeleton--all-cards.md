# old_skeleton: ten card bodies

Exact card content from the evaluated bundle. The actor reads these on demand.

## card-002

# card-002 — The proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment

**Applicability**
O1: Check that the proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment.

**Proof skeleton**
O2: Establish set equality through pointwise membership equivalence.
- O3: For the forward direction, derive membership in the image union from membership in either image using union and image definitions.
- For the reverse direction:
  - O4: When image membership is assumed on one side, introduce a chosen witness satisfying the corresponding source membership and mapping relation.
    - Rationale: the reverse direction requires exposing the existential witness because merely asserting union-image membership does not give the solver enough information.
  - O5: Prove the witness belongs to the union.
    - Rationale: the chosen witness connects the image definition to union membership.
  - O6: Derive the union image membership and obtain the contradiction.
- O7: If the verifier warns about low-confidence triggers for the quantified equivalence, accept the automatic trigger or annotate the equivalence to give the solver reliable membership triggers.
  - Note: trigger annotation can suppress a warning after the logical witness step succeeds, but the success depends on that witness.

**Validation**
O8: Run the verifier after adding the witness step and confirm zero errors; then run the proof-safety comparison.
O9: Confirm no assumptions or specification changes were introduced.

**Avoid when**
O10: A directly applicable library lemma proves the same obligation and its premises hold, because manual witness reasoning is then avoidable.
O11: Do not assume after a successful proof that the trigger annotation alone was responsible for discharging the obligation; it may only have suppressed a warning.

---

## card-017

# card-017 — A proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure

## Applicability
- **O1** — Enter this route when a proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure.

## Do not apply when
- **O13** — The folding operator does not have a decreasing cardinality argument, or the empty and nonempty unfoldings do not produce the equality needed to transfer finiteness.

## Proof structure
- **O9** — Either add a recursive proof helper and call it from the required function, or if allowed add the decreasing clause and reason directly inside the required function.
  - This is the implementation choice for O2–O8, not a proof step after induction has finished.
- **O2** — Use induction on the cardinality of the finite input set.
  - **Zero-cardinality case**
    - **O3** — Show the folded result equals the empty set, and conclude from this equality that it is finite.
  - **Nonzero-cardinality case**
    - **O4** — Choose an element from the finite input set.
    - **O5** — Assert that removing the chosen element strictly lowers the cardinality.
    - **O6** — Recursively prove finiteness for the result over the remaining set.
      - Dependency: O6 is available after O5 has established a smaller cardinality.
    - **O7** — Assert that the full fold equals the recursive result with the image of the chosen element inserted.
      - Rationale link: O10 explains why this equality is expected.
    - **O8** — Conclude finiteness through the fact that inserting into a finite set preserves finiteness.


## Why
- **O10** — The recursive equality mirrors the recursive definition of the fold, so the full result is exposed as an insert over a smaller fold.
- **O11** — Induction on a strictly decreasing cardinality gives termination and transfers the finiteness property step by step.

## Validate
- **O12** — Rerun Verus until every function verifies with no errors, then run the proof-safety comparison and expect a zero exit and no differences.


---

## card-022

# card-022 — Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions

## Applicability

Use this route when:

- O1: Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions; concrete fold-bound and append-length obligations continue to fail even after those generic lemmas are invoked.

Avoid this route when:

- O8: The generic lemma already instantiates correctly, or the recursive structure does not provide a decreasing well-founded measure.

## Proof obligations

- O2: Introduce specialized recursive lemmas over the concrete element type.
- O3: Include preconditions that every element is well-formed for serialization and that each element satisfies the chosen numeric bound.
- O4: In the empty case, unfold the fold with enough fuel and prove the zero or empty result.
- O5: In the nonempty case, remove the final element, establish the elementwise facts for the shortened sequence, call the lemma on the remainder, unfold the fold again, and add the final element's contribution to the bound.
- O6: The concrete fold expression matches the specialized lemma's conclusion exactly, whereas the higher-order lemma retains an abstract function argument that the solver does not rewrite into the concrete folding function.

## Non-executable structural layout

```text
specialized recursive lemma over the concrete element type    // O2
  preconditions:
    every element is well-formed for serialization            // O3
    each element satisfies the chosen numeric bound          // O3
  recursive proof by cases on the sequence
    decreasing measure required                                // O8 guard
    case empty:
      unfold the fold with enough fuel                        // O4
      prove the zero or empty result                         // O4
    case nonempty:
      remove the final element                               // O5
      establish the elementwise facts for the shortened sequence // O5
      call the lemma on the remainder                        // O5
      unfold the fold again                                  // O5
      add the final element's contribution to the bound      // O5
  conclusion connection:
    concrete fold expression matches specialized lemma conclusion // O6
```

## Validation

- O7: The previously failing concrete fold-bound and append-length assertions discharge after replacement. Verus reports no errors and the proof-only safety comparison passes.


---

## card-029

# card-029 — A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier

## Applicability
Use this route only when O1 below holds, and enforce the limits in O8 below.

## Supported obligations and layout

```text
O1  entry check:
     target : equality between two temporal predicates
     body    : empty or cannot discharge the postcondition
     given   : existing helper rules already describe
               - commuting a universal temporal quantifier
               - moving the always construct across that quantifier

O2  instantiate the helper that moves always across the universal
     with two pointwise predicate families that differ only in
     whether the always wraps the implication.

O3  for each index:
       discharge the helper precondition for O2
         reduce both entailment directions to self-entailment
         of the same always predicate
       local reflexivity assertion is sufficient.

O4  instantiate the helper that commutes a plain implication
     through the universal quantifier.

O5  chain the resulting equalities under congruence of always
     to close the target.

O6  why:
       O2 and O4 helper postconditions rewrite the left side
       into the right side in two compatible steps.
       O3 precondition is definitional reflexivity after the
       always operation is applied to the same underlying predicate,
       so it does not require a new lemma.

O7  validate:
       rerun Verus and expect verification with zero proof errors;
       then run the behavior-preservation checker and confirm it
       exits successfully.
       observed traces: O2-O5 helper chain closed the postcondition;
       a missing local proof block produced a syntax error and was
       fixed by adding a local reflexivity assertion.

O8  avoid/limits:
       do not attempt to unfold all temporal definitions globally;
       do not introduce a new universal temporal rule;
       do not skip the precondition assertion for the always-moving
       helper (O2), because its external body still requires that
       premise to be discharged.
```

---

## card-037

# card-037 — A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically

## Entry condition
- **O1** A whole-sequence validity or range property is available.
- **O2** An assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically.

## Proof layout
- **O3** Introduce a small proof-only helper that takes the whole-sequence property and an in-bounds index and concludes the element property.
  - *Why:* A bounded forall often requires an explicit instantiation step; a lemma localizes that step and keeps the loop body legible.
- **O4** Call that helper in the loop body.
  - **O5** Use the concrete indexed term at the call site so the quantifier trigger can match.
  - *Dependency:* O4 is supported by O5; O3 provides the called helper.

## Validation
- **O6** Rerun Verus; the previously failing element assertion or call precondition should become provable.

## Rejection / Avoid
- **O7** Do not apply when the element property is not actually derivable from the whole-sequence assumption under the available bounds, or when the index is not guaranteed to be in range.


---

## card-058

# card-058 — A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed

## Applicability / entry

O1: Confirm the premise is an entailment or validity statement. The triggering failure is: asserting only its conclusion does not activate the premise's universal quantifier, and Verus reports the inferred assertion as failed.

## Rejection / avoid

O2: Stop and use a helper lemma or a different unfolding if the premise is not an entailment or validity over the same execution type, or if the selected implication term does not match the premise's syntactic form.

## Route

```text
entry: O1; evaluate rejection guard O2
if O2 rejects, leave this route; otherwise O3 -> O4 -> O7
O5 is a local constraint; O6 is rationale

O3: Before using the premise at a concrete execution:
      assert the full implication-form satisfaction for that execution
      not just the conclusion
O4: Then, for the same execution:
      apply the implication with the antecedent
      conclude the right-hand side
O5: Constraint for O3-O4:
      use the existing universal hypothesis
      do not add any new trusted fact
O6: Rationale for O3-O4:
      an entailment expands to a universal quantifier over executions
      SMT instantiation often needs the surface form of the implication
      applied to the chosen execution
O7: Validate:
      re-run Verus
      previously failing assertion should be discharged
      final target should close
```

---

## card-060

# card-060 — Verus compile errors say a struct field is not a method when a stored spec function is applied directly to an argument in a proof

**Applicability / rejection**
- O1: This route applies when Verus reports compile errors saying a struct field is not a method while a stored spec function is applied directly to an argument in a proof.
- O9: Do not use this route when the field is not a function-valued field, or the equality can be proved by another supplied lemma without pointwise expansion; fixing syntax does not replace a missing logical fact.

**Non-executable proof/check layout**
```text
O1  (entry condition, above)
  O2  Rewrite each occurrence so the field projection is parenthesized first, then apply it to the index argument.
      O5 supports O2: the field stores a function value rather than a method, so the parser needs the projection to be treated as a callable value.
  O7  Re-run Verus after O2; compile errors should vanish.
  O3  After fixing parsing, check whether Verus reports a missing trigger for the universal equality.
    O4  If O3 reports a missing trigger, add explicit trigger annotations to both sides of the equality.
        O6 supports O4: the explicit trigger lets the pointwise equality quantifier instantiate at arbitrary indices so the execution equality lemma can be applied.
    O8  If the subsequent trigger error appears, adding the explicit trigger should enable verification; the final proof should pass with all proof functions verified and the safety comparison clean.
```

**Validation / limits**
- O7 and O8 are the validation checks. O9 is the rejection boundary.

---

## card-062

# card-062 — Verus reports an empty or incomplete proof body for a temporal stability postcondition, and the target predicate is a finite conjunction of always-lifted state predicates

## Applicability
- **O1.** Enter this route only when Verus reports an empty/incomplete proof body for a temporal stability postcondition and the target predicate is a finite conjunction of always-lifted state predicates.

## Reuse path
- **O2.** Inspect the local temporal rule definitions; identify the existing stability rule and the existing conjunction-combination machinery or helper macro already present in the file.
- **O3.** Reuse the existing stability and conjunction-combination machinery/helper macro; do not unfold the temporal definitions by hand.
- **O4.** Apply the reused machinery/helper macro to each lifted state predicate in the same left-to-right order as the target predicate is constructed.

## Why this path is supported
- **O5.** The supplied rules provide exactly the two needed logical facts: every always predicate is stable, and stable predicates are closed under binary conjunction.
- **O6.** Left-to-right application connects the proof steps to the target's left-associated structure.

## Validation
- **O7.** Re-run Verus and confirm the postcondition is discharged with only pre-existing warnings; then run the proof-only safety comparison and inspect that only the proof body changed.

## Avoid when
- **O8.** Do not use this route when the target is not a finite conjunction of always-lifted predicates, or when the expected local stability and conjunction rules are absent or incompatible with the definitions.

---

## card-070

# card-070 — A postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails

## Route applicability

- **O1** The route applies when a postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails.
- **O13** Do not apply when built-in extensional equality for those objects already suffices without manual pointwise evidence.
- **O14** Do not apply when the arithmetic identity needed for the index shift is not available in scope.

## Supported proof structure

- **O2** Prove the two semantic entailment directions separately.
  - Direction from nested application to single application:
    - **O3** Instantiate the outer and inner quantified statements at a concrete index and at zero.
  - Direction from single application to nested application:
    - **O4** Instantiate at the sum of two arbitrary indices.
  - In each direction:
    - **O5** Prove equality of the underlying state or suffix objects pointwise at every index using simple arithmetic identities and the supplied pointwise-equality lemma.
      - <derive pointwise equality for each index using simple arithmetic identities and the supplied pointwise-equality lemma>
    - **O6** Then invoke the supplied equality lemma for the spec-level objects.

## Why this structure

- **O7** Equality of function-like specification objects is not derived automatically.
- **O8** The prover needs pointwise equality plus the supplied lemma that turns pointwise equality into object equality.
- **O9** The remaining mathematical work is arithmetic over indices and the existing object equality lemmas.

## Validation boundary

- **O10** Run Verus after each entailment direction and ensure both verify before invoking the final equality lemma.
- **O11** Then run the proof-only safety comparison.
- **O12** Do not add new trusted bodies or weaken contracts; existing trusted declarations are background only.

---

## card-076

# card-076 — A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases

**Trigger**
O1 — A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases.

**Repair route**
```text
O2 — Inline the local aliases back into the expanded suffix and predicate expressions used by the helper's preconditions.

O3 — Then explicitly assert each quantified hypothesis the helper requires, using the following branch:
  O4 — open a conditional branch on the antecedent of that hypothesis;
  O5 — in that branch, assert the exact quantified trigger term of that hypothesis to force instantiation of the always fact.
```

**Why**
O6 — Local aliases can change the syntactic form that Verus uses to match quantifier triggers, so the propagated fact is not instantiated at the call site.
O7 — Inlining restores the exact forms, and the explicit assertion of the trigger term invokes the universal fact.

**Validation**
O8 — Rerun Verus; the helper's quantified precondition should now be discharged and the surrounding proof should close.
O9 — Confirm Lynette passes.

**Avoid when**
O10 — The aliases are not implicated in trigger matching, or the necessary facts are not available as trusted quantified facts.
O11 — Changing trigger selection is not required; accepting an existing automatic trigger to suppress a note is different from forcing instantiation.

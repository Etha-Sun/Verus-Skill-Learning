# old_pseudocode: ten card bodies

Exact card content from the evaluated bundle. The actor reads these on demand.

## card-002

# card-002 — The proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment

## Applicability

The proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when set/image equality remains open after a bare membership assertion:
    if a library lemma already matches and its premises hold: use that route instead
    obligation: pointwise membership equivalence
        direction forward:
            under <membership in either image>:
                <derive membership in the image union from union/image definitions>
        direction reverse:
            under <image membership on the active side>:
                choose <source witness with source membership and mapping relation>
                <prove witness membership in the union>
                <derive union-image membership and the required contradiction>
    <close set equality through the established membership equivalence>
    if the quantified equivalence receives a low-confidence-trigger warning:
        accept the automatic trigger OR annotate reliable membership triggers
        do not attribute proof success to warning suppression alone
    <check Verus zero errors, proof-safety comparison, unchanged assumptions/specifications>
```

## Rationale and evidence limits

The reverse direction requires exposing the existential witness because merely asserting union-image membership does not give the solver enough information.

The chosen witness connects the image definition to union membership.

Trigger annotation can suppress a warning after the logical witness step succeeds, but the success depends on that witness.

## Validation

Run the verifier after adding the witness step and confirm zero errors; then run the proof-safety comparison.

Confirm no assumptions or specification changes were introduced.

## Rejection limits

A directly applicable library lemma proves the same obligation and its premises hold, because manual witness reasoning is then avoidable.

Also avoid assuming after a successful proof that the trigger annotation alone was responsible for discharging the obligation; it may only have suppressed a warning.


---

## card-017

# card-017 — A proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure

## Applicability

A proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when an empty proof leaves finiteness of a finite-set fold open:
    stop if cardinality does not decrease or required branch equalities are unavailable
    choose proof placement:
        recursive proof helper, called from the target function
        OR, if permitted, direct proof with a decreasing clause in the target
    induction on cardinality of the finite input set:
        case cardinality = zero:
            <show fold result equals the empty set>
            <conclude finiteness>
        case cardinality > zero:
            choose <an input element>
            <prove removal strictly decreases cardinality>
            <recursively prove finiteness of the fold on the remainder>
            <show full fold equals insertion of the chosen image into the smaller fold>
            <conclude finiteness by preservation under insertion>
    <check all functions with Verus, then proof-safety exit zero and no differences>
```

## Rationale and evidence limits

The recursive equality mirrors the recursive definition of the fold, so the full result is exposed as an insert over a smaller fold.

Induction on a strictly decreasing cardinality gives termination and transfers the finiteness property step by step.

## Validation

Rerun Verus until every function verifies with no errors, then run the proof-safety comparison and expect a zero exit and no differences.

## Rejection limits

The folding operator does not have a decreasing cardinality argument, or the empty and nonempty unfoldings do not produce the equality needed to transfer finiteness.


---

## card-022

# card-022 — Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions

## Applicability

Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions.
Concrete fold-bound and append-length obligations continue to fail even after those generic lemmas are invoked.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when generic fold lemmas pass but concrete fold-bound/append-length goals still fail:
    stop if the generic lemma already instantiates or no decreasing measure exists
    specialized recursive lemma over the concrete element type:
        requires <every element is serialization-well-formed>
        requires <every element satisfies the selected numeric bound>
        case empty sequence:
            <unfold the fold with sufficient fuel>
            <prove the zero or empty result>
        case nonempty sequence:
            bind <sequence with final element removed> and <final element>
            <establish elementwise premises for the shortened sequence>
            <apply the recursive lemma to the remainder>
            <unfold the concrete fold>
            <add the final element's contribution to the bound>
    <check the original concrete assertions, Verus zero errors, and proof-only safety>
```

## Rationale and evidence limits

The concrete fold expression matches the specialized lemma's conclusion exactly, whereas the higher-order lemma retains an abstract function argument that the solver does not rewrite into the concrete folding function.

## Validation

The previously failing concrete fold-bound and append-length assertions discharge after replacement.

Verus reports no errors and the proof-only safety comparison passes.

## Rejection limits

The generic lemma already instantiates correctly, or the recursive structure does not provide a decreasing well-founded measure.


---

## card-029

# card-029 — A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier

## Applicability

A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when temporal equality remains open and both quantified-temporal helper rules exist:
    do not globally unfold temporal definitions or invent a universal temporal rule
    bind <two pointwise families differing in where always wraps the implication>
    obligation: precondition of the always-through-universal helper
        for each family index:
            direction first pointwise predicate entails second:
                <reduce to self-entailment of the same always predicate>
                <discharge with a local reflexivity assertion>
            direction second pointwise predicate entails first:
                <reduce to the same self-entailment and assert reflexivity>
    <apply the always-through-universal helper with its premise established>
    <apply the helper commuting plain implication through the universal>
    <chain the two equalities under congruence of always to close the target>
    <check Verus zero errors and behavior preservation>
```

## Rationale and evidence limits

The two helper postconditions rewrite the left side into the right side in two compatible steps.

The precondition is definitional reflexivity after the always operation is applied to the same underlying predicate, so it does not require a new lemma.

## Validation

Rerun Verus and expect verification with zero proof errors; then run the behavior-preservation checker and confirm it exits successfully.

In the observed traces this helper chain closed the postcondition, while a missing local proof block produced a syntax error and was fixed by adding a local reflexivity assertion.

## Rejection limits

Do not attempt to unfold all temporal definitions globally or introduce a new universal temporal rule.

Do not skip the precondition assertion for the always-moving helper, because its external body still requires that premise to be discharged.


---

## card-037

# card-037 — A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically

## Applicability

A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when a whole-sequence property is available but a loop-index element assertion fails:
    stop if bounds are missing or the element property is not derivable
    proof-only element helper:
        requires <whole-sequence property> and <index in bounds>
        <derive the element property at that index>
    in the loop body, at the current index:
        <use the concrete indexed term for quantifier matching>
        <call the helper with the sequence property and index bound>
    <rerun Verus on the failed element assertion or callee precondition>
```

## Rationale and evidence limits

A bounded forall often requires an explicit instantiation step; a lemma localizes that step and keeps the loop body legible.

## Validation

Rerun Verus; the previously failing element assertion or call precondition should become provable.

## Rejection limits

The element property is not actually derivable from the whole-sequence assumption under the available bounds, or the index is not guaranteed to be in range.


---

## card-058

# card-058 — A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed

## Applicability

A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when asserting a consequence fails to instantiate an entailment/validity premise:
    if execution types differ or the implication term does not match the premise:
        leave this route; use a helper lemma or a different unfolding
    at the concrete execution required by the goal:
        <assert the full implication-form satisfaction from the universal hypothesis>
        under <the implication's antecedent holds here>:
            <apply the established implication>
            <conclude its right-hand side at this execution>
    do not add a new trusted fact
    <rerun Verus on the failed assertion and final target>
```

## Rationale and evidence limits

An entailment expands to a universal quantifier over executions, and SMT instantiation often needs the surface form of the implication applied to the chosen execution.

## Validation

Re-run Verus; the previously failing assertion should be discharged and the final target should close.

## Rejection limits

The premise is not an entailment or validity over the same execution type, or the selected implication term does not match the premise's syntactic form; use a helper lemma or a different unfolding in that case.


---

## card-060

# card-060 — Verus compile errors say a struct field is not a method when a stored spec function is applied directly to an argument in a proof

## Applicability

Verus compile errors say a struct field is not a method when a stored spec function is applied directly to an argument in a proof.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when applying a stored spec-function field produces a field-is-not-a-method error:
    stop if this is not a function-valued field or a supplied lemma avoids expansion
    for each affected occurrence:
        <parenthesize the field projection, then apply it to the index argument>
    <rerun Verus to check that parsing succeeds>
    if the next diagnostic is a missing trigger for universal equality:
        within that quantified equality:
            <annotate explicit trigger terms on both sides>
        <recheck verification of all proof functions and proof-safety comparison>
    syntax repair leaves any missing logical fact as an obligation
```

## Rationale and evidence limits

The field stores a function value rather than a method, so the parser needs the projection to be treated as a callable value.

The explicit trigger then lets the pointwise equality quantifier instantiate at arbitrary indices so the execution equality lemma can be applied.

## Validation

Re-run Verus; compile errors should vanish.

If a subsequent trigger error appears, adding the explicit trigger should enable verification, and the final proof should pass with all proof functions verified and the safety comparison clean.

## Rejection limits

The field is not a function-valued field, or the equality can be proved by another supplied lemma without pointwise expansion; fixing syntax does not replace a missing logical fact.


---

## card-062

# card-062 — Verus reports an empty or incomplete proof body for a temporal stability postcondition, and the target predicate is a finite conjunction of always-lifted state predicates

## Applicability

Verus reports an empty or incomplete proof body for a temporal stability postcondition, and the target predicate is a finite conjunction of always-lifted state predicates.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when a finite conjunction of always-lifted state predicates has an open stability goal:
    <inspect local stability and conjunction rules or the existing helper macro>
    stop if the target shape differs or those rules are absent/incompatible
    following the target's left-to-right construction:
        for each always-lifted state predicate:
            <apply the available individual stability machinery>
        <combine stability facts with the local conjunction machinery>
        <match the target's left-associated structure>
    <check the postcondition, pre-existing warnings only, and proof-body-only changes>
```

## Rationale and evidence limits

The supplied rules express exactly the two logical facts needed: every always predicate is stable, and stable predicates are closed under binary conjunction.

Using them in the same order lets Verus connect the proof steps to the target's left-associated structure.

## Validation

Re-run Verus and confirm the postcondition is discharged with only pre-existing warnings, then run the proof-only safety comparison and inspect that only the proof body changed.

## Rejection limits

The target is not a finite conjunction of always-lifted predicates, or the expected local stability and conjunction rules are absent or incompatible with the definitions.


---

## card-070

# card-070 — A postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails

## Applicability

A postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when equality of once-applied and twice-applied spec objects remains open:
    stop if built-in extensionality suffices or needed index arithmetic is unavailable
    direction nested application entails single application:
        <instantiate the outer/inner quantified statements at a concrete index and zero>
        for arbitrary state/suffix index:
            <prove equality of underlying values using the available arithmetic identities>
        <apply the supplied pointwise-to-object equality lemma>
        <close and verify this entailment direction>
    direction single application entails nested application:
        for two arbitrary indices:
            <instantiate the single-application fact at their sum>
            for arbitrary state/suffix index:
                <prove equality of underlying values using the available arithmetic identities>
            <apply the supplied pointwise-to-object equality lemma>
        <close and verify this entailment direction>
    after both directions verify:
        <invoke the supplied equality lemma for the spec-level objects>
    <check proof-only safety; add no trusted bodies and weaken no contracts>
```

## Rationale and evidence limits

Equality of function-like specification objects is not derived automatically.

The prover needs pointwise equality plus the supplied lemma that turns pointwise equality into object equality.

The remaining mathematical work is arithmetic over indices and the existing object equality lemmas.

## Validation

Run Verus after each entailment direction and ensure both verify before invoking the final equality lemma.

Then run the proof-only safety comparison.

Do not add new trusted bodies or weaken contracts; existing trusted declarations are background only.

## Rejection limits

Built-in extensional equality for those objects already suffices without manual pointwise evidence, or the arithmetic identity needed for the index shift is not available in scope.


---

## card-076

# card-076 — A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases

## Applicability

A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when a helper's quantified stability premise fails after facts were propagated to a suffix:
    stop if aliases are not implicated or required quantified facts are unavailable
    <expand local aliases to the suffix/predicate expressions in the helper contract>
    for each required quantified hypothesis:
        for arbitrary values bound by that hypothesis:
            under <its antecedent>:
                <assert the exact quantified trigger term to instantiate the always fact>
                <establish the required consequence in this scope>
        <close the quantified hypothesis>
    do not confuse using an existing trigger with changing trigger selection
    <rerun Verus on the helper precondition and enclosing proof; check Lynette>
```

## Rationale and evidence limits

Local aliases can change the syntactic form that Verus uses to match quantifier triggers, so the propagated fact is not instantiated at the call site.

Inlining restores the exact forms, and an explicit assertion of the trigger term invokes the universal fact.

## Validation

Rerun Verus; the helper's quantified precondition should now be discharged and the surrounding proof should close.

Confirm Lynette passes.

## Rejection limits

The aliases are not implicated in trigger matching or the necessary facts are not available as trusted quantified facts.

Changing trigger selection is not required; accepting an existing automatic trigger to suppress a note is different from forcing instantiation.

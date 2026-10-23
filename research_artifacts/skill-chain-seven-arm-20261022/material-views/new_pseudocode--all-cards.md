# new_pseudocode: ten card bodies

Exact card content from the evaluated bundle. The actor reads these on demand.

## new-001

# Check recursive set finiteness at the active branch

## Applicability

The current failed obligation is a finiteness postcondition for the set produced by recursively accumulating over a finite input set, and the proof body is empty or has just introduced an unverified recursive proof routine; the remaining goal is to connect the accumulator's branch behavior to finiteness without assuming a missing premise.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when recursive-set finiteness remains open in an empty or newly recursive proof:
    <inspect the failed postcondition, accumulator declaration, and existing branches>
    bind <finite input set> under <its explicit finiteness premise>
    stop if that premise cannot be justified
    inspect only branch relations available in the current definitions:
        case empty input:
            <establish the empty-result relation and its finiteness>
            if unresolved: leave the relation open; add no speculative equality
            do not apply reduced-input recursion checks to this branch
        case nonempty input:
            bind <input with one element removed> and <its accumulated result>
            <check the active result's insertion relation to that reduced result>
            if insertion relation is known AND reduced-result finiteness is proved:
                <check preservation under insertion and connection to the target>
            if insertion preservation remains open:
                <inspect reduced-input finiteness and strict decrease before any recursive call>
                leave missing equalities as obligations, not additional assumptions
            stop if neither finite reduced result nor justified smaller-input step is available
    <rerun the same finiteness postcondition>
    if verified: record the branch relation used
    otherwise: check whether missing smaller-input finiteness is the blocker
```

## Rationale and evidence limits

Reviewed windows show edits that added a recursive proof routine and a call from the target before passing Verus runs, but each edit was bundled with no admitted intermediate check; the necessity of the routine split, equality form, or particular branch condition is therefore not established.

## Validation

Re-run the same finiteness postcondition after the branch-level probe; if the postcondition is now established, record which branch relation was used, and if it remains unsatisfied, check whether a missing smaller-input finiteness premise is the remaining blocker rather than the final finiteness transfer.

## Rejection limits

Stop this route if the finite-input premise cannot be justified.

In a recursive branch, stop if neither a supported finite reduced result nor a justified smaller-input recursive step is available.

These recursive conditions do not apply to the empty branch; do not assume a missing branch relation.


---

## new-002

# Check loop-local availability of a callee premise

## Applicability

The current obstruction is a failed callee precondition or local assertion inside a loop over a packet collection.
A required per-element property may be available outside the loop but absent or unapplied at the current call site; diagnose this from the current source rather than requiring the historical sequence of failed attempts.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when a loop-local packet assertion or callee precondition fails:
    <inspect the diagnostic, preceding invariants, and available packet/endpoint facts>
    at the current call site and index:
        bind <collection, view length, index, pre-loop endpoint, in-loop client state>
        bind <current invariant set and legally scoped proof helpers>
        <compare required packet validity and endpoint equality with same-index invariants>
        do not infer a match from a sequence property present elsewhere
        case required sequence property missing from invariants:
            <prove the current entry facts establish the property>
            <prove every iteration preserves the property>
            only after both: propose the property as an invariant
            absence alone is a diagnostic, not a reason to abandon this check
        case property present but unapplied at this index:
            <inspect an available instantiation rule and its actual preconditions>
            <try one justified application>
        do not invent a helper or assume either missing obligation
        <rerun the same verifier command>
        if the same precondition still fails:
            <compare view/index identity, pre-loop vs in-loop endpoint, and newly missing facts>
        if the failure moves: classify the new obligation separately
    stop if property/bounds cannot be derived or invariant-proved, no applicable rule exists,
        or the probe would assume a premise or change executable behavior
```

## Rationale and evidence limits

Reviewed attempts show that sequence-level assertions placed before and inside the loop, and added but uninvoked proof helpers, did not clear the loop-body assertion or precondition failures.

This does not establish whether the missing support is quantifier instantiation, precondition visibility, a missing loop invariant, or a combination of these.

## Validation

Run the same verifier command and inspect whether the same callee precondition or assertion is still reported.

If the failure moves to a new location, classify the new obligation separately before making another edit.

## Rejection limits

Stop when the required property or index bound cannot be derived in the relevant scope or proved as an invariant, when no applicable instantiation rule is available, or when the probe would assume a premise or change executable behavior.

A fact absent from the existing invariant list is a diagnostic condition, not by itself a reason to abandon checking whether it can be established.


---

## new-003

# Match a quantified step to the helper execution scope

## Applicability

The current Verus diagnostic reports a precondition failure at a call to the forward-preservation helper.
The unfilled requirement is the universal step relation saying that whenever the invariant and the next predicate hold at a suffix, the invariant holds at the immediate suffix.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when the forward-preservation helper's universal step precondition fails:
    <inspect the call-site proof, helper contract, and propagated universal always-fact>
    <identify aliases of the base execution and implication predicate>
    bind <base execution, relation to starting index, predicates from the actual contract>
    for arbitrary step index in the contract's base-execution scope:
        <compare the suffix step relation with the quantified helper requirement>
        <compare aliases with the expanded forms used to establish the always-fact>
        do not treat the original and base executions as interchangeable
        <prove the required step relation at this suffix, not the helper's final conclusion>
        if the probe fails:
            hold this suffix; inspect which side of the step relation is unjustified
            if no expression mismatch is found:
                <check the universal always-fact at the base execution and shifted index>
                if neither is available nor derivable: stop; do not alter the prerequisite
    <verify the local step proof and the original quantified precondition>
    only after verification: call the forward-preservation helper
    treat another unresolved conclusion as a separate obligation
    stop if the call/premise is absent, the step is underivable, or the contract would change
```

## Rationale and evidence limits

Reviewed training windows show the same forward helper precondition failed after the field-call syntax repair.

Later attempts explicitly proved the quantified step relation before that call, and the indexed checks then reported seven verified with no errors; one passing branch retained local aliases, and another later change altered the way the step assertion was expressed, so neither inlining nor a single assertion form is established as necessary.

## Validation

Re-run the same Verus command and inspect the same quantified helper precondition and the added local step proof.

Confirm their verification before treating the step fact as available; a diagnostic merely moving elsewhere is not independent evidence that each earlier assertion passed.

Treat another unresolved conclusion as a separate obligation.

## Rejection limits

Stop when the helper call is absent, the quantified step is not among the current premises or derivable from the supplied rules, the failure is not the helper precondition, or the only route would assume the missing step or alter the original contract.


---

## new-004

# Locate a supported witness in set-image membership reasoning

## Applicability

The current failed obligation is a set-extensionality assertion: a membership equivalence between the image of a union and the union of two images.
The failure is an assertion failure rather than a parse or name-resolution error, and the active proof block already binds the two domain sets and the mapping function.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when image/union membership equivalence fails in an existing quantified proof:
    this route concerns assertion failure, not parsing or name resolution
    <inspect the assertion, active branch, and available membership/image-equality premises>
    in the current range-element scope:
        bind <range element, two domain sets, mapping, active branch>
        <compare both image/union forms and identify the open direction>
        under <membership in one of the two images>:
            check for <source element with source membership and image equal to current element>
            if that source element and its relations are in scope:
                <derive the required union containment from them>
            otherwise, if the source element is not yet bound:
                <inspect whether active image membership and definitions justify existence>
                if justified:
                    <check the installed selection construct and its contract>
                    <bind the element and prove its membership and image relation>
                otherwise: leave the witness connection unresolved
            do not invent premises, repeat containment alone, or use an unspecified repair
    <rerun the original assertion or enclosing postcondition>
    if failure shifts: inspect branch premises; do not assume the witness relation suffices
    stop for unsupported existence/relations or illegal selection, not mere lack of a bound witness
```

## Rationale and evidence limits

In this training group, after the parse structure was corrected, the quantified membership-equivalence assertion still failed, and an earlier branch that only asserted the negative union membership also failed.

A later nearby transition changed the source-element extraction form and a subsequent run reported success, but only a single nearby edit separates those checks and the exact mechanism was not isolated, so witness reasoning remains an uncertain hypothesis rather than a known necessity.

## Validation

Re-run the same failed assertion or enclosing postcondition and inspect whether the original membership-equivalence obligation closes or the same line still fails.

Treat a new or shifted failure as a signal to inspect the active branch premises rather than assume the source-element relation is sufficient.

## Rejection limits

Stop if neither an existing source-element premise nor a justified existence argument supports the required image relation, if the selection construct cannot be applied legally, or if the probe would introduce an assumption.

A missing already-bound witness alone does not rule out deriving one from image membership; historical success establishes no universal witness necessity.


---

## new-005

# Expose an entailment instance before using its consequence

## Applicability

A final entailment obligation remains open even though pointwise and temporal-lifting reasoning is present.
Determine whether that reasoning is actually proved or only attempted, and whether the given temporal hypothesis has been instantiated for the execution at the open obligation.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when final entailment stays open despite pointwise and temporal-lifting reasoning:
    <distinguish proved reasoning from attempted reasoning and check premise instantiation>
    <inspect entailment, its quantified premise, predicates, and the actual connecting contract>
    for arbitrary execution required by the current obligation:
        under <a justified source-satisfaction branch>:
            bind <source and destination predicates from the current contract>
            <compare the hypothesis's full instance at this execution with the local expression>
            <identify the required antecedent and actual source-to-destination direction>
            if the declaration and current premises justify the instance:
                <derive its expression from the current declaration, not a historical formula>
                <assert and verify the full hypothesis instance>
                <derive its consequence; the destination property is still an obligation>
                if the instance is justified but final entailment is still open:
                    <check pointwise implication and temporal lifting in the required direction>
                    if a link is unavailable: leave it open and inspect its premises
            keep consequences in this execution/premise scope; reverse no implication
        stop if scope, instance, or connection is unjustifiable; weaken no specification
    <rerun the same final entailment postcondition>
    if verified: stop
    if an intermediate assertion fails:
        <use its location to distinguish missing instantiation from pointwise strengthening>
        do not repeat the same edit without a changed diagnostic
```

## Rationale and evidence limits

Reviewed endpoints include a failed direct entailment assertion and failed generic transitivity reasoning.

A later passing state added full premise instances, removed the helper and changed the outer assertion together; the suffix reasoning was already present.

This supports a conditional inspection of premise instances, not isolated causality, an observed SMT firing or a universally sufficient expression.

## Validation

Re-run the verifier on the same final entailment postcondition.

If it passes, stop; if an intermediate assertion fails, use its location to decide whether the missing link is hypothesis instantiation or the pointwise strengthening, and do not repeat the same edit without a changed diagnostic.

## Rejection limits

Stop this route if no source-satisfaction scope is justified, the hypothesis cannot be instantiated at the required execution, or the actual pointwise/temporal connection cannot be derived.

Do not assume obligations, reverse an implication, or weaken the specification.


---

## new-006

# Match temporal stability composition to local rule contracts

## Applicability

An empty or incomplete proof body leaves a temporal stability postcondition open for a conjunction of temporal predicates constructed from state predicates.
Inspect the exact temporal wrappers: local stability and conjunction rules may be used only when their real input shapes and premises match the goal.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when temporal stability of a conjunction remains open:
    <inspect the failed function/body, parameters, exact postcondition, and local rules>
    the postcondition and missing premises remain unproved
    <compare validity/stability wrapper, conjunction structure, and each operand's input shape>
    if the actual stability and conjunction contracts license this target:
        <derive it using local composition in the target's structural order>
        preserve specifications and termination measures
        <run Verus and read full diagnostics>
        if composition fails:
            <inspect the actual rule or macro expansion before decomposing>
            only if those contracts justify decomposition:
                for each operand, in its valid scope:
                    <prove that operand's required stability fact>
                <discharge every premise of the conjunction rule>
                one proved operand does not establish any other operand
            otherwise: leave the unsupported connection open
    otherwise: stop for missing/incompatible premises or rule types
    <recheck the original postcondition; aggregate success is not per-step evidence>
    if failure repeats: inspect the first new diagnostic and change strategy
    if the obligation is discharged: stop; do not edit code/specs to remove old warnings
```

## Rationale and evidence limits

Reviewed evidence shows one adjacent source edit that replaced an empty proof body with a proof-only invocation of local composition machinery over four lifted state predicates.

Before the edit, Verus reported the postcondition unsatisfied with zero verified and one error; after the edit, it reported one verified and zero errors.

The observation is aggregate and correlational: it does not isolate which helper-internal obligation, conjunct count, or ordering property was necessary, and no counterfactual body or alternative ordering was reviewed.

## Validation

Re-run the same Verus obligation on the current candidate and read the full diagnostics.

Interpret an aggregate one-verified, zero-errors result only as closure of the whole postcondition for this file, not as proof that each local proof step was independently discharged.

If the same failure repeats, inspect the first new diagnostic and change strategy rather than repeating the same edit.

## Rejection limits

Stop when the proof function no longer has the empty-body postcondition and the same obligation is discharged by Verus, or when a missing or incompatible premise or rule type prevents lawful application.

Do not continue merely to remove pre-existing warnings or change executable and specification code.


---

## new-007

# Inspect permitted interfaces for a closed serialization definition

## Applicability

The current failed diagnostic is a reveal rejection on the closed little-endian conversion function, or a serialized-length assertion that cannot see the closed function body.
This operation applies when the closed-function diagnostic or an equivalent serialized-length obligation remains the immediate failed verification goal and the bytes module is available for inspection.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when closed-conversion reveal/length fails and the bytes module can be inspected:
    <inspect closed/open declarations, connector postconditions, and open-length facts>
    bind <current 64-bit value, closed term, open term, visible trait-body scope>
    do not bind or reveal the inaccessible closed body
    <compare open length consequences and the exact closed-equals-open relation needed>
    if a connector with that consequence is present:
        <invoke the connector>
        <assert the expected length of the open term only>
        <rerun and check whether the open-length fact is discharged>
        only after it is discharged: attempt transfer to the closed term
    if no connector consequence is available OR open length is not discharged:
        do not retry revealing the closed function
        <check whether a general module byte-width fact instantiates at this value>
        only if it does: attempt to connect that fact to the closed term
    <rerun the original closed-term length obligation and locate any remaining transfer gap>
    stop if neither open definition nor explicit connector consequence is available,
        or open length would require an unadmitted premise
```

## Rationale and evidence limits

One reviewed window showed that the closed little-endian conversion function rejected a reveal diagnostic, and a separate later transition removed that path in favor of an open form and connector version but immediately produced a syntax error at an ensures.

This supports inspecting the allowed open and connector relationships, not copying that later formula.

## Validation

Re-run the verifier after any permitted connector call or open-length assertion, and check the original serialized-length obligation.

Determine whether the original closed-term length assertion is now discharged or whether the transfer step remains the failing goal.

## Rejection limits

Stop if the bytes module provides neither an open definition nor an explicit consequence relating the closed and open forms, or if the open length cannot be established without an unadmitted premise.


---

## new-008

# Check pointwise entailment premises of an equality helper

## Applicability

The current Verus diagnostic reports a postcondition failure at the end of an empty proof body for the target equality, and the existing temporal predicate definitions and helper proof functions are available unchanged.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when equality remains open and existing temporal definitions/helpers are available:
    <inspect the failed target and identify a helper requiring pointwise mutual entailment>
    stop if that premise, the types, or the helper conditions do not match
    bind <current predicates and two families from the actual helper contract>
    for arbitrary element of the required family type, within its proof scope:
        do not presume family equality or reuse historical lambda arguments
        <compare both required entailment directions with entailment's definition here>
        if this helper precondition is the unresolved subgoal:
            direction first bound predicate entails second:
                <prove a separate local entailment assertion>
            direction second bound predicate entails first:
                <prove a separate local entailment assertion>
            <rerun Verus before any helper invocation>
        if no precondition mismatch is found OR either direction fails:
            <inspect entailment/validity/implication/always definitions at this element>
            do not assume reflexivity or proceed to an equality chain
    <close the required pointwise pair after both local assertions are verified>
    only after both assertions are accepted: invoke the matched helper
    if either direction cannot be justified: stop this route
    <rerun the original equality target; accept only its reported verification>
    a changed diagnostic separates obligations; shell success alone proves no helper contribution
```

## Rationale and evidence limits

Reviewed evidence bundles a single source transition that adds two pointwise predicate families, a mutual entailment assertion, and two helper calls, with aggregate Verus moving from 0 verified, 1 error to 1 verified, 0 errors.

This collectively associates the additions with closure but does not isolate any component; per-assertion and safety-comparison results are not present in the indexed window.

## Validation

Re-run Verus on the same target postcondition.

Interpret a changed diagnostic as separation of the new precondition obligation; only accept if the original postcondition is reported verified, and do not infer helper contribution from a shell exit status alone.

## Rejection limits

Stop this route if the candidate helper does not require the relevant pointwise entailment premises, its types or conditions do not match the current equality obligation, or either direction cannot be justified.

Do not reuse the historical lambda names or equality chain as a fixed template; the empty-body observation is evidence context, not a requirement to match the historical source verbatim.


---

## new-009

# Inspect legal trigger terms at a quantifier diagnostic

## Applicability

The verifier currently reports that a quantifier in the pointwise execution equality proof has no inferred trigger, after field-projection syntax has already been corrected enough to reach trigger inference.
What remains to be proved is the pointwise equality over an arbitrary index that is needed as a precondition for the execution equality lemma, without assuming any missing premise.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when syntax now parses but a pointwise-equality quantifier has no inferred trigger:
    <inspect the reported equality, bound index, two function applications, and annotations>
    within that quantifier's scope:
        bind <current executions and its arbitrary index>
        introduce no concrete witness, suffix-arithmetic expression, or later obligation
        <compare diagnostic and existing annotations; inspect legal call/projection shapes>
        if the diagnostic rejects the available terms as triggers: stop this action
        if no legal existing body term is annotated:
            <select one existing call/projection term; annotate that single term>
            do not copy a historical side choice or annotate multiple terms at once
        <rerun the same verifier command>
        if missing-trigger persists after one legal annotation:
            <inspect the reported shape and select a different existing call/projection term>
        if no legal term remains or proposition/specification would need alteration:
            stop; report that the equality formulation needs restructuring
    <inspect the next diagnostic on the same equality obligation>
    if the local trigger error disappears: mark only that failure addressed
    treat a later failed obligation as a separate action; stop this action once it passes
```

## Rationale and evidence limits

Reviewed evidence shows that after field-projection syntax was corrected, a missing-trigger diagnostic appeared on the pointwise equality quantifier, and later checks with trigger annotation on at least one existing term passed.

No minimal trigger placement is established because the available fork shares the earlier prefix, so the evidence supports bounded inspection, not a universal side or sufficiency claim.

## Validation

Rerun the same verifier command on the same pointwise equality obligation and read the next diagnostic.

If the missing-trigger diagnostic disappears and the enclosing proof reaches its next obligation, treat only that local trigger failure as addressed; if a later proof failure appears at another location, classify it as a separate decision rather than evidence that the annotation is sufficient elsewhere.

## Rejection limits

Stop if no legal function-call or field-projection term remains available as a trigger in the current quantifier, if the diagnostic says the current terms cannot be used as triggers, or if further annotations would require changing the specification or the asserted proposition.

Also stop this action when the same obligation passes and open a separate action for any subsequent failed obligation.


---

## new-010

# Check antecedent scope inside a quantified implication proof

## Applicability

A proof assertion inside a universally quantified entailment fails verification, and the diagnostic indicates that an outer implication does not make its antecedent available in the body; the inner obligation depends on that antecedent.

## Proof skeleton

Schematic proof layout, NOT executable Verus. Angle-bracketed slots are
unresolved obligations or current-context inspections, never trusted helpers.
A branch marked `under` uses only a justified premise in that branch.

```text
when an inner quantified-entailment assertion lacks its outer implication's antecedent:
    <inspect the inner obligation, assertion body, and enclosing quantified formula>
    for the arbitrary quantified values already required by this proof scope:
        bind <only the execution/index needed by the inner obligation>
        <compare the needed premise with the hypotheses actually in scope>
        if the antecedent is only part of an expression, not a body hypothesis:
            <inspect the accepted implication-assertion form and current proposition>
            case antecedent holds, where the proposition requires its consequent:
                <establish the inner obligation under that justified antecedent>
                retain existing local steps only within their valid scopes
            complementary case:
                <discharge the remaining case obligation>
            <close the enclosing implication obligation>
        do not require a fixed disjunction formula or equality-lemma chain
        <rerun the same assertion; classify any warnings as fatal or nonfatal>
        if the assertion still fails:
            <inspect the actual missing premise, index, or object relation>
            if existing equality reasoning is relevant:
                <check that it concerns those same objects>
            otherwise: leave that equality route unused
            do not repeat the same formulation or invent a relation
    stop if antecedent support is unjustifiable or supported branching/connections do not close it
```

## Rationale and evidence limits

Neighboring evidence shows a source state using an outer implication with explicit antecedent branches produced a passing Verus check, while another state rewriting to a disjunction also passed without visible implication warnings.

The check alone does not isolate the branch from retained equality proof steps, and warning absence is based on visible stdout only.

## Validation

Re-run the same Verus check on the same failed assertion and confirm whether the inner assertion is now discharged; if warnings remain, record whether they are fatal or nonfatal.

## Rejection limits

Stop if the antecedent cannot be made available without assuming or admitting it, or if the obligation is not discharged after explicit branching and supported equality connections; do not infer that a passing check validates a missing premise.

# Proof grounding and comment-only proof rejection

## When

The failure is a missing logical fact or inert definitional/temporal fact, not a parse/type or trusted-policy exception. Consult this reference for comment-only proof rejection, proof-term requirements, and temporal/higher-order unfolding.

## Procedure

1. Inspect the actual definition of the relevant function or combinator with `assert ... by(compute_only)`, `reveal`, `unfold`, or existing equational lemmas before choosing induction/decomposition.
2. Search for already verified lemmas whose ensures/postconditions directly support the needed equality, length, membership, fold, or state-transition fact.
3. Before invoking any lemma or macro, inspect its requires clauses and prove each missing precondition with explicit assertions or small helper derivations.
4. Replace comment-only proof blocks with actual proof terms: `assert`, `assert ... by`, lemma calls, local `let` facts, induction, or explicit forall assertions.
5. Comments that merely state `By X, Y follows` are not proof terms, and a proof block whose body contains only explanatory comments is not a proof term. Each claimed consequence must become a checked `assert`, `assert ... by`, `reveal`/`unfold`, lemma invocation, `let` binding, induction step, or explicit forall assertion; otherwise delete the comments. Never leave an `assert ... by { /* ... */ }` block or a proof-function body with only comments or empty braces.
6. When the obligation involves temporal or higher-order predicates (`TempPred`, `entails`, `valid`, `implies`, `always`, `satisfied_by`, `lift_state`/`lift_action`), unfold these definitions into explicit quantifier facts for arbitrary executions and positions before using transitivity or entailment. Inside nested quantifier bodies, explicitly assert the relevant requires-clause antecedent; do not rely only on intermediate predicate names.
7. Rerun after grounding; do not introduce empty `ext_equal` proofs, `external_body` proof functions with `unimplemented!()`, or equivalent trusted shortcuts.

## Check

The verifier accepts the previously missing fact via a visible definitional step, verified lemma, or explicit proof term. Every proof block and proof-function body contains an actual proof term, not only comments or empty braces. No new trusted axiom or unimplemented proof-function body is present.

## Limitations

- This reference does not authorize syntax/literal/cast/parenthesis edits; those are only justified for parse/type errors.
- This reference does not authorize environment/macro/generated-code repairs, whole-proof restructuring, or trusted shortcuts.
- This reference does not replace exact-target diff and trust-boundary review.

## Contraindications

- Do not leave comment-only proof blocks or empty proof-function bodies.
- Do not rely on intermediate predicate names without unfolding temporal/higher-order definitions when the obligation is temporal/higher-order.
- Do not introduce new trusted helpers, `admit`, `assume`, `external_body` proof functions with `unimplemented!()`, or empty or axiom-like `ext_equal` declarations.
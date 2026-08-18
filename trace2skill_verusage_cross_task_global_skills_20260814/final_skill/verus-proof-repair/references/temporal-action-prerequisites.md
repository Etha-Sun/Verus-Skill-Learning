# Temporal and action lemma prerequisites

## Procedure

1. If a lemma call fails because of a missing precondition or incompatible argument, inspect the lemma signature and derive the missing prerequisite; do not delete the call as the repair.
2. For temporal/action rules such as `wf1` or `leads_to_stable`, prove each required state-level condition separately before invoking the rule; do not skip stability, action-establishment, enabledness, or similar derived conditions.
3. When connecting an `always` or `entails` antecedent to an action fact, first prove the state-level implication as an assertion or helper lemma, then lift it through the temporal rule.

## Check

- Any failed lemma call is retained and its missing precondition or incompatible argument is made explicit and derived before reuse.
- Each state-level condition required by a temporal/action rule is proved separately before the rule is invoked.
- State-to-temporal proof order is explicit: state-level implication first, then temporal lifting.

## Limitations

- This route is for proof-order and lemma-prerequisite failures, not for replacing missing temporal rules with assumptions or trusted shortcuts.
- It does not cover Verus parse/type errors or unrelated container/sequence equality obligations.

## Contraindications

- Do not delete a failing lemma call just because its precondition or argument is not yet available.
- Do not skip stability, action-establishment, enabledness, or similar derived state-level conditions when invoking temporal/action rules such as `wf1` or `leads_to_stable`.
- Do not lift an `always`/`entails` antecedent to an action fact before proving the underlying state-level implication as an assertion or helper lemma.

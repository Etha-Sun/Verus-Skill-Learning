# Quantified proof-block antecedent and binder scope failures

## Scope

- Consult when: Proof block, assert-forall, or helper precondition fails inside quantified implication
- Consult when: Diagnostic says antecedent not assumed or facts disappear because binder was shadowed by a fresh symbol
- Not for: Failure is a trigger-inference diagnostic
- Not for: Needed logical premise is genuinely absent, not a scope or antecedent problem

<a id="helper-precondition-implication-branch-verbatim"></a>
## Helper precondition failure under quantified implication: explicit antecedent branch (card-074)

Source cards: card-074

**Trigger:** Verus reports a precondition not satisfied for a helper call inside a quantified assertion whose body contains an implication, or warns that the implication antecedent is not assumed in the assertion body.
**Action:** Replace the single implication assertion with an explicit conditional branch on the antecedent. In the branch where the antecedent holds, perform the helper call and assert the conclusion; in the other branch, assert the trivial conclusion when possible. This discharges the same goal while making the antecedent available as a local hypothesis.
**Why:** Verus does not reliably assume the antecedent for an implication nested inside an assert-forall proof block, so helper preconditions requiring that antecedent cannot be discharged. An explicit branch introduces the hypothesis directly.
**Validate:** Rerun Verus; the previously failing precondition should disappear and the enclosing quantified assertion should close. Continue to run Lynette to ensure proof-only changes are safe.
**Avoid when:** The implication is part of the actual specification, requires, or ensures and cannot be rewritten as a code branch; or the goal is already discharged by a supplied lemma with both case obligations.

## Conditional links

- When When the actual diagnostic is an implication whose antecedent is not assumed, rather than a trigger inference failure.: [trigger-inference-annotation/original-card-057](trigger-inference-annotation.md#original-card-057)
- When When the diagnostic is a quantified implication antecedent that is not being assumed rather than a method/field error.: [function-field-projection-syntax/card-015-verbatim](function-field-projection-syntax.md#card-015-verbatim)
- When When the failing diagnostic is a weak implication missing its antecedent rather than trigger inference.: [trigger-inference-annotation/original-card-018](trigger-inference-annotation.md#original-card-018)

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route annotates quantifier patterns; antecedent/binder route makes the hypothesis or existing bound value available.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Trigger-annotation route changes quantifier trigger patterns when trigger inference fails; this family repairs missing implication antecedent or binder shadowing inside quantified proof blocks.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route asserts/applies an already in-scope universal fact at a concrete term; this family fixes antecedent availability or binder scope needed before such instantiation.

- Related [post-verification-cleanup](post-verification-cleanup.md): Post-verification cleanup applies only after verification succeeds; this family addresses active missing-antecedent or binder-scope failures before verification, while card-069 reminds users to treat warning cleanup separately.

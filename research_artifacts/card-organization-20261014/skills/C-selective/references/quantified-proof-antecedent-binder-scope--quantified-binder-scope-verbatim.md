# Quantified proof-block antecedent and binder scope failures

## Scope

- Consult when: Proof block, assert-forall, or helper precondition fails inside quantified implication
- Consult when: Diagnostic says antecedent not assumed or facts disappear because binder was shadowed by a fresh symbol
- Not for: Failure is a trigger-inference diagnostic
- Not for: Needed logical premise is genuinely absent, not a scope or antecedent problem

<a id="quantified-binder-scope-verbatim"></a>
## Quantified proof-block binder scope and antecedent assumptions (card-023)

Source cards: card-023

**Trigger:** A proof block for a quantified implication fails to use its antecedent, so later index-bound or quantified facts are unavailable inside the block. Warnings may state that the antecedent is not being assumed.
**Action:** Use the quantified binder directly rather than shadowing it with a new symbol. If the proof block does not assume its implication antecedent, use the dedicated proof implication operator named implies by the current diagnostic, or explicitly branch on that antecedent before any operation requiring it.
**Why:** Some block connectives do not assume the antecedent, and redeclaring the witness as a fresh unconstrained symbol severs the connection to the quantified value. This causes otherwise valid facts about that witness to disappear.
**Validate:** The quantified proof block and its final target discharge. Verus reports no errors, and the proof-only safety comparison passes.
**Avoid when:** The needed index or bound premise is genuinely absent, or there is no binder-scope or missing-antecedent issue. The implication behavior was observed in Verus 0.2025.09.12.bb1f342; confirm current diagnostics rather than rewriting arbitrary implications.

## Conditional links

- When When the actual diagnostic is an implication whose antecedent is not assumed, rather than a trigger inference failure.: [trigger-inference-annotation/original-card-057](trigger-inference-annotation.md#original-card-057)
- When When the diagnostic is a quantified implication antecedent that is not being assumed rather than a method/field error.: [function-field-projection-syntax/card-015-verbatim](function-field-projection-syntax.md#card-015-verbatim)
- When When the failing diagnostic is a weak implication missing its antecedent rather than trigger inference.: [trigger-inference-annotation/original-card-018](trigger-inference-annotation.md#original-card-018)

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route annotates quantifier patterns; antecedent/binder route makes the hypothesis or existing bound value available.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Trigger-annotation route changes quantifier trigger patterns when trigger inference fails; this family repairs missing implication antecedent or binder shadowing inside quantified proof blocks.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route asserts/applies an already in-scope universal fact at a concrete term; this family fixes antecedent availability or binder scope needed before such instantiation.

- Related [post-verification-cleanup](post-verification-cleanup.md): Post-verification cleanup applies only after verification succeeds; this family addresses active missing-antecedent or binder-scope failures before verification, while card-069 reminds users to treat warning cleanup separately.

# Quantified proof-block antecedent and binder scope failures

## Scope

- Consult when: Proof block, assert-forall, or helper precondition fails inside quantified implication
- Consult when: Diagnostic says antecedent not assumed or facts disappear because binder was shadowed by a fresh symbol
- Not for: Failure is a trigger-inference diagnostic
- Not for: Needed logical premise is genuinely absent, not a scope or antecedent problem

## Rules

- [Missing antecedent in quantified proof implication: diagnostic-supported implies or explicit branch/disjunction](#missing-antecedent-quantified-proof)
- [Quantified proof-block binder scope and antecedent assumptions (card-023)](#quantified-binder-scope-verbatim)
- [Helper precondition failure under quantified implication: explicit antecedent branch (card-074)](#helper-precondition-implication-branch-verbatim)

<a id="missing-antecedent-quantified-proof"></a>
## Missing antecedent in quantified proof implication: diagnostic-supported implies or explicit branch/disjunction

Source cards: card-006, card-069

**Trigger:**
- Inside a proof block for a quantified assertion or universal implication, Verus fails an inner assertion or lemma call even though the body appears to have the needed antecedent, and diagnostics warn that the implication form in that quantified proof assertion does not assume the antecedent for the body.
- The failure may occur in a proof block inside a universal assertion; Verus may report an inner assertion failure or warn that the top-level implication in such an assertion does not assume the antecedent in the body.

**Premises:**
- The failure is the missing-antecedent diagnostic for the quantified proof assertion; the route is not for trigger-inference failures and does not supply a genuinely absent different logical premise.

**Action:**
- Use the dedicated proof implication operator named implies by the current Verus diagnostic.
- For the implies route, use it only when the current diagnostic confirms it in the observed Verus version and check that the antecedent warning disappears.
- Explicitly branch on the antecedent before deriving the consequent.
- As an equivalent-disjunction form of the branch route, prove the implication through an equivalent disjunction and branch explicitly on the antecedent inside the quantified proof, then derive the consequent under that branch.
- Check nested assertions separately; do not rewrite unrelated specification implications.
- These are alternative routes, not mandatory combined steps; choose one route unless independent evidence supports combining them.

**Why:**
- Verus treats the two logical implication notations differently in asserted quantified proof bodies; the form that is not recognized as antecedent-assuming leaves the body without the needed hypothesis, causing failed lemma preconditions and assertions.
- In the observed Verus version, the plain implication arrow inside an asserted universal does not make the antecedent available inside the proof body, leaving inner instantiations without the needed assumption. Explicit branching makes that assumption available.
- A free function named implication was not in scope, and guessing an import or qualified path produced unrelated compile failures; that guess is not evidence either logical strategy is impossible.

**Validate:**
- Re-run Verus and confirm the previously failed preconditions or inner assertions disappear; full verification reaches the expected number of verified functions with zero errors.
- Run the proof-only safety comparison tool afterward.
- Treat verification success separately from later warning cleanup; warnings do not prove that every trigger or antecedent change was logically necessary.

**Avoid when:**
- The antecedent is already available or the failure needs a different logical premise; this route does not address unrelated missing facts.
- Do not rewrite unrelated specification implications.
- Do not use a missing-helper guess or guessed import/qualified path as evidence that either logical strategy is impossible.

**Version scope:**
- Dedicated proof implication operator behavior was observed in Verus 0.2025.09.12.bb1f342; confirm the current diagnostic and language support rather than assuming this behavior in every version.


<a id="quantified-binder-scope-verbatim"></a>
## Quantified proof-block binder scope and antecedent assumptions (card-023)

Source cards: card-023

**Trigger:** A proof block for a quantified implication fails to use its antecedent, so later index-bound or quantified facts are unavailable inside the block. Warnings may state that the antecedent is not being assumed.
**Action:** Use the quantified binder directly rather than shadowing it with a new symbol. If the proof block does not assume its implication antecedent, use the dedicated proof implication operator named implies by the current diagnostic, or explicitly branch on that antecedent before any operation requiring it.
**Why:** Some block connectives do not assume the antecedent, and redeclaring the witness as a fresh unconstrained symbol severs the connection to the quantified value. This causes otherwise valid facts about that witness to disappear.
**Validate:** The quantified proof block and its final target discharge. Verus reports no errors, and the proof-only safety comparison passes.
**Avoid when:** The needed index or bound premise is genuinely absent, or there is no binder-scope or missing-antecedent issue. The implication behavior was observed in Verus 0.2025.09.12.bb1f342; confirm current diagnostics rather than rewriting arbitrary implications.

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

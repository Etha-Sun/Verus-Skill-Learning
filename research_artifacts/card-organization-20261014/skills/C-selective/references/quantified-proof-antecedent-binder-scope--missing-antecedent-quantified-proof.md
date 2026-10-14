# Quantified proof-block antecedent and binder scope failures

## Scope

- Consult when: Proof block, assert-forall, or helper precondition fails inside quantified implication
- Consult when: Diagnostic says antecedent not assumed or facts disappear because binder was shadowed by a fresh symbol
- Not for: Failure is a trigger-inference diagnostic
- Not for: Needed logical premise is genuinely absent, not a scope or antecedent problem

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


## Conditional links

- When When the actual diagnostic is an implication whose antecedent is not assumed, rather than a trigger inference failure.: [trigger-inference-annotation/original-card-057](trigger-inference-annotation.md#original-card-057)
- When When the diagnostic is a quantified implication antecedent that is not being assumed rather than a method/field error.: [function-field-projection-syntax/card-015-verbatim](function-field-projection-syntax.md#card-015-verbatim)
- When When the failing diagnostic is a weak implication missing its antecedent rather than trigger inference.: [trigger-inference-annotation/original-card-018](trigger-inference-annotation.md#original-card-018)

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route annotates quantifier patterns; antecedent/binder route makes the hypothesis or existing bound value available.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Trigger-annotation route changes quantifier trigger patterns when trigger inference fails; this family repairs missing implication antecedent or binder shadowing inside quantified proof blocks.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route asserts/applies an already in-scope universal fact at a concrete term; this family fixes antecedent availability or binder scope needed before such instantiation.

- Related [post-verification-cleanup](post-verification-cleanup.md): Post-verification cleanup applies only after verification succeeds; this family addresses active missing-antecedent or binder-scope failures before verification, while card-069 reminds users to treat warning cleanup separately.

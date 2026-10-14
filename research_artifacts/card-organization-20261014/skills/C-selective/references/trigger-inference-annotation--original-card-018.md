# Explicit triggers for quantifier inference failures

## Scope

- Consult when: Verus cannot infer triggers for a quantified assertion, choose, or witness term; cards 018/057 also cover a separately diagnosed missing antecedent
- Not for: Only a low-confidence trigger note remains after successful verification
- Boundary: A missing-antecedent-only case is not card-034's trigger-only case; it remains within cards 018/057's stated coverage
- Not for: A genuinely missing logical premise, rather than trigger selection or antecedent availability

<a id="original-card-018"></a>
## Original card-018

Source cards: card-018

**Trigger:** An assertion or witness selection in a proof body fails because the verifier reports that it cannot infer quantifier triggers, or it warns that the weak implication does not assume its antecedent inside an assertion proof.
**Action:** If the proof body lacks an implication antecedent, use the dedicated proof implication operator named implies by the current diagnostic, or explicitly branch on the antecedent. If the error instead concerns trigger inference, annotate a relevant atomic witness term or per-witness entailment term that mentions the bound variable. Recheck these two diagnoses independently; neither repair is automatically needed for the other.
**Why:** The weak implication form does not make the antecedent available inside the proof body, so follow-up assertions fail. Explicit triggers guide quantifier instantiation and avoid the automatic trigger inference failure.
**Validate:** Rerun Verus after changing to assuming implication and adding triggers; the prior trigger-inference errors should disappear, and the proof should verify. Then run the safety comparison.
**Avoid when:** No missing-antecedent or trigger-inference diagnostic is present, or the proof lacks a genuine logical premise. The implication behavior was observed in Verus 0.2025.09.12.bb1f342; check the installed language before selecting that operator.

## Conditional links

- When After fixing the field projection syntax, when Verus reports a missing trigger for the universal equality.: [function-field-projection-syntax/merged-field-projection-before-apply](function-field-projection-syntax.md#merged-field-projection-before-apply)
- When After the field access is fixed, when Verus cannot infer a trigger for the universal pointwise equality.: [function-field-projection-syntax/card-028-verbatim](function-field-projection-syntax.md#card-028-verbatim)

- Distinguish from [post-verification-cleanup](post-verification-cleanup.md): Cleanup route applies only after the proof verifies; trigger annotation here addresses an active trigger-inference diagnostic.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Trigger rule annotates quantifier patterns for an active trigger-inference failure; antecedent/binder rule makes the hypothesis or existing bound value available.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Trigger rule changes quantifier annotations; universal-instantiation rule asserts or applies an already-available universal fact at a concrete term without a trigger-inference diagnostic.

- Related [post-verification-cleanup](post-verification-cleanup.md): Trigger rule responds only to an active trigger-inference failure; cleanup route applies after verification for warning or safety-comparison differences.

- Related [universal-equivalence-pointwise](universal-equivalence-pointwise.md): Universal-equivalence route proves pointwise equivalence before choosing triggers or directional lemmas; trigger rule only annotates an existing quantifier.

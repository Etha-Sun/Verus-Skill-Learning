# Explicit triggers for quantifier inference failures

## Scope

- Consult when: Verus reports it cannot automatically infer triggers for a quantified assertion, choose, or witness term
- Not for: Only a low-confidence trigger note remains after successful verification
- Not for: Failure is a missing antecedent rather than trigger selection

## Rules

- [Original card-018](#original-card-018)
- [Original card-034](#original-card-034)
- [Original card-057](#original-card-057)

<a id="original-card-018"></a>
## Original card-018

Source cards: card-018

**Trigger:** An assertion or witness selection in a proof body fails because the verifier reports that it cannot infer quantifier triggers, or it warns that the weak implication does not assume its antecedent inside an assertion proof.
**Action:** If the proof body lacks an implication antecedent, use the dedicated proof implication operator named implies by the current diagnostic, or explicitly branch on the antecedent. If the error instead concerns trigger inference, annotate a relevant atomic witness term or per-witness entailment term that mentions the bound variable. Recheck these two diagnoses independently; neither repair is automatically needed for the other.
**Why:** The weak implication form does not make the antecedent available inside the proof body, so follow-up assertions fail. Explicit triggers guide quantifier instantiation and avoid the automatic trigger inference failure.
**Validate:** Rerun Verus after changing to assuming implication and adding triggers; the prior trigger-inference errors should disappear, and the proof should verify. Then run the safety comparison.
**Avoid when:** No missing-antecedent or trigger-inference diagnostic is present, or the proof lacks a genuine logical premise. The implication behavior was observed in Verus 0.2025.09.12.bb1f342; check the installed language before selecting that operator.

<a id="original-card-034"></a>
## Original card-034

Source cards: card-034

**Trigger:** Verus reports that it could not automatically infer triggers for a quantified assertion or choose expression used to select a witness.

**Action:** Add an explicit trigger annotation to a term in the quantified body that mentions the bound variable and is relevant to the later witness use. If a parallel quantified assertion exists, give it the same explicit treatment. Then re-run Verus and treat the disappearance of the trigger error as only the next diagnostic step, not as completion of the proof.

**Why:** Without a designated trigger term, Verus cannot decide how to instantiate the quantifier. An explicit annotation supplies the term that the SMT solver can match against ground facts. This was necessary in both temporal tasks before further proof obligations could be reached.

**Validate:** Re-run Verus and confirm the trigger-inference error is gone. If the error reappears at another choose or assertion, inspect that new bound-variable occurrence rather than duplicating the same annotation mechanically.

**Avoid when:** The proof already verifies and only a low-confidence automatic trigger note remains. Do not add trigger annotations merely to suppress warning output after success, and do not assume that manual trigger selection is required or helpful for every quantifier; it should be driven by an actual trigger-inference diagnostic.

<a id="original-card-057"></a>
## Original card-057

Source cards: card-057

**Trigger:** Verus reports that it cannot automatically infer triggers for a universal assertion, or warns that an implication used inside a quantified assertion does not assume the antecedent in the proof body.
**Action:** Treat trigger inference and missing antecedents as separate diagnostics. For a missing antecedent, use the dedicated proof implication operator named implies in the current diagnostic or branch explicitly on the antecedent. For trigger inference, annotate the predicate application on the quantified state or suffix that later instantiation actually needs. Rerun before deciding whether the other repair is also necessary.
**Why:** Automatic trigger selection and antecedent assumption differ between implication forms. Explicit triggers ensure the quantifier is instantiated at the concrete terms used later, and the assuming form lets local reasoning use the antecedent.
**Validate:** Re-run Verus; the trigger-inference error and implication warnings should disappear, leaving any remaining proof obligation visible.
**Avoid when:** The proof failure requires a new logical premise rather than either reported diagnostic. The implication behavior was observed in Verus 0.2025.09.12.bb1f342; confirm local syntax and the current warning. Successful-proof warning cleanup alone is not evidence that these steps were needed to construct the proof.

## Conditional links

- When After fixing the field projection syntax, when Verus reports a missing trigger for the universal equality.: [function-field-projection-syntax/merged-field-projection-before-apply](function-field-projection-syntax.md#merged-field-projection-before-apply)
- When After the field access is fixed, when Verus cannot infer a trigger for the universal pointwise equality.: [function-field-projection-syntax/card-028-verbatim](function-field-projection-syntax.md#card-028-verbatim)

- Distinguish from [post-verification-cleanup](post-verification-cleanup.md): Cleanup route applies only after the proof verifies; trigger annotation here addresses an active trigger-inference diagnostic.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Trigger rule annotates quantifier patterns for an active trigger-inference failure; antecedent/binder rule makes the hypothesis or existing bound value available.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Trigger rule changes quantifier annotations; universal-instantiation rule asserts or applies an already-available universal fact at a concrete term without a trigger-inference diagnostic.

- Related [post-verification-cleanup](post-verification-cleanup.md): Trigger rule responds only to an active trigger-inference failure; cleanup route applies after verification for warning or safety-comparison differences.

- Related [universal-equivalence-pointwise](universal-equivalence-pointwise.md): Universal-equivalence route proves pointwise equivalence before choosing triggers or directional lemmas; trigger rule only annotates an existing quantifier.

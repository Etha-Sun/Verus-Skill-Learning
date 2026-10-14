# Explicit triggers for quantifier inference failures

## Scope

- Consult when: Verus cannot infer triggers for a quantified assertion, choose, or witness term; cards 018/057 also cover a separately diagnosed missing antecedent
- Not for: Only a low-confidence trigger note remains after successful verification
- Boundary: A missing-antecedent-only case is not card-034's trigger-only case; it remains within cards 018/057's stated coverage
- Not for: A genuinely missing logical premise, rather than trigger selection or antecedent availability

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

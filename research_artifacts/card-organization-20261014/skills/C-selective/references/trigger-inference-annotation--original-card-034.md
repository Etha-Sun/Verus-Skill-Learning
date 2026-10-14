# Explicit triggers for quantifier inference failures

## Scope

- Consult when: Verus cannot infer triggers for a quantified assertion, choose, or witness term; cards 018/057 also cover a separately diagnosed missing antecedent
- Not for: Only a low-confidence trigger note remains after successful verification
- Boundary: A missing-antecedent-only case is not card-034's trigger-only case; it remains within cards 018/057's stated coverage
- Not for: A genuinely missing logical premise, rather than trigger selection or antecedent availability

<a id="original-card-034"></a>
## Original card-034

Source cards: card-034

**Trigger:** Verus reports that it could not automatically infer triggers for a quantified assertion or choose expression used to select a witness.

**Action:** Add an explicit trigger annotation to a term in the quantified body that mentions the bound variable and is relevant to the later witness use. If a parallel quantified assertion exists, give it the same explicit treatment. Then re-run Verus and treat the disappearance of the trigger error as only the next diagnostic step, not as completion of the proof.

**Why:** Without a designated trigger term, Verus cannot decide how to instantiate the quantifier. An explicit annotation supplies the term that the SMT solver can match against ground facts. This was necessary in both temporal tasks before further proof obligations could be reached.

**Validate:** Re-run Verus and confirm the trigger-inference error is gone. If the error reappears at another choose or assertion, inspect that new bound-variable occurrence rather than duplicating the same annotation mechanically.

**Avoid when:** The proof already verifies and only a low-confidence automatic trigger note remains. Do not add trigger annotations merely to suppress warning output after success, and do not assume that manual trigger selection is required or helpful for every quantifier; it should be driven by an actual trigger-inference diagnostic.

## Conditional links

- When After fixing the field projection syntax, when Verus reports a missing trigger for the universal equality.: [function-field-projection-syntax/merged-field-projection-before-apply](function-field-projection-syntax.md#merged-field-projection-before-apply)
- When After the field access is fixed, when Verus cannot infer a trigger for the universal pointwise equality.: [function-field-projection-syntax/card-028-verbatim](function-field-projection-syntax.md#card-028-verbatim)

- Distinguish from [post-verification-cleanup](post-verification-cleanup.md): Cleanup route applies only after the proof verifies; trigger annotation here addresses an active trigger-inference diagnostic.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): Trigger rule annotates quantifier patterns for an active trigger-inference failure; antecedent/binder rule makes the hypothesis or existing bound value available.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Trigger rule changes quantifier annotations; universal-instantiation rule asserts or applies an already-available universal fact at a concrete term without a trigger-inference diagnostic.

- Related [post-verification-cleanup](post-verification-cleanup.md): Trigger rule responds only to an active trigger-inference failure; cleanup route applies after verification for warning or safety-comparison differences.

- Related [universal-equivalence-pointwise](universal-equivalence-pointwise.md): Universal-equivalence route proves pointwise equivalence before choosing triggers or directional lemmas; trigger rule only annotates an existing quantifier.

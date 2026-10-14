# Function-valued field versus method access

## Scope

- Consult when: A method is mistaken for a field, a stored function field is called as a method, or pointwise record equality has the related syntax/trigger failure
- Consult when: Card-015's separate case matches a quantified-proof missing-antecedent diagnostic
- Not for: None of these method/field, pointwise-equality trigger, or missing-antecedent diagnostics is present
- Boundary: The stored-function rule excludes genuine methods; that exclusion does not exclude card-015's method-as-field case

<a id="card-015-verbatim"></a>
## Mixed method/function-field and missing quantified antecedent diagnostics (verbatim card-015)

Source cards: card-015

**Trigger:** Newly added proof code produces Verus errors that a method name is being taken as a field, or a struct field is being called as a method; alternatively, quantified assertion bodies warn or fail because an implication antecedent is not being assumed.
**Action:** Distinguish an actual method from a field storing a function. Call methods normally; select a function-valued field before applying it. Separately, if a quantified proof assertion lacks its antecedent, use the diagnostic's dedicated proof implication operator, named implies in the observed version, or an explicit conditional guard before deriving the conclusion.
**Why:** Verus distinguishes Rust methods from stored function fields, and the quantifier-body implication form controls whether the antecedent is available inside the proof. Rewriting these constructs consistently removes parse and type errors and makes the intended case assumptions available to the solver.
**Validate:** Rerun the Verus checker after corrections and require proof diagnostics or zero errors; run the proof-safety comparison tool and require exit zero.
**Avoid when:** The diagnostic is not a method-versus-field or missing-antecedent error. The implication behavior was observed in Verus 0.2025.09.12.bb1f342; confirm current diagnostics before changing syntax, and do not alter specification meaning.

- Distinguish from [record-function-field-equality](record-function-field-equality.md): This route corrects projection/application syntax only; it does not establish pointwise equality or record equality.

- Related [record-function-field-equality](record-function-field-equality.md): This family corrects projection/application syntax only; record-function-field-equality establishes logical field and record equality after the syntax is corrected.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Card-060 and card-028 include a conditional follow-up to add explicit triggers for universal pointwise equality after syntax repair; trigger-inference-annotation handles standalone trigger-inference failures without the initial field-call parse error.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): The second branch of verbatim card-015 overlaps with quantified-proof-antecedent-binder-scope's missing-antecedent repair. It remains inside the verbatim rule because the source card bundles both diagnostics.

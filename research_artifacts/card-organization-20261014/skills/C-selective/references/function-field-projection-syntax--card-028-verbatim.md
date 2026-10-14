# Function-valued field versus method access

## Scope

- Consult when: A method is mistaken for a field, a stored function field is called as a method, or pointwise record equality has the related syntax/trigger failure
- Consult when: Card-015's separate case matches a quantified-proof missing-antecedent diagnostic
- Not for: None of these method/field, pointwise-equality trigger, or missing-antecedent diagnostics is present
- Boundary: The stored-function rule excludes genuine methods; that exclusion does not exclude card-015's method-as-field case

<a id="card-028-verbatim"></a>
## Pointwise record equality with function-valued fields (verbatim card-028)

Source cards: card-028

**Trigger:** A newly introduced pointwise equality proof on a record containing a function-valued field fails, either because the field is accessed like a method, or because the verifier cannot infer a trigger for the universal pointwise equality.
**Action:** Access the field first and then apply the contained function to the index; add an explicit trigger to the pointwise universal equality. After proving pointwise equality, assert equality of the two function fields, which then yields equality of the containing records.
**Why:** The field stores a function, not a method, so the application must be explicit. A trigger supplies the pattern the quantifier needs. Pointwise equality of functions is not equal to equality of the function fields or records until field equality is asserted.
**Validate:** Run the verifier after each small repair. In the observed continuation, this moved the proof from a syntax error through a trigger-inference error to a cleared postcondition, and the larger stability proof subsequently passed.
**Avoid when:** Avoid leaving the field applied as a method call or omitting the trigger if the verifier cannot infer it. Do not treat pointwise equality as record equality before establishing equality of the function-valued field.

- Distinguish from [record-function-field-equality](record-function-field-equality.md): This route corrects projection/application syntax only; it does not establish pointwise equality or record equality.

- Related [record-function-field-equality](record-function-field-equality.md): This family corrects projection/application syntax only; record-function-field-equality establishes logical field and record equality after the syntax is corrected.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Card-060 and card-028 include a conditional follow-up to add explicit triggers for universal pointwise equality after syntax repair; trigger-inference-annotation handles standalone trigger-inference failures without the initial field-call parse error.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): The second branch of verbatim card-015 overlaps with quantified-proof-antecedent-binder-scope's missing-antecedent repair. It remains inside the verbatim rule because the source card bundles both diagnostics.

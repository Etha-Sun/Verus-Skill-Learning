# Function-valued field versus method access

## Scope

- Consult when: A method is mistaken for a field, a stored function field is called as a method, or pointwise record equality has the related syntax/trigger failure
- Consult when: Card-015's separate case matches a quantified-proof missing-antecedent diagnostic
- Not for: None of these method/field, pointwise-equality trigger, or missing-antecedent diagnostics is present
- Boundary: The stored-function rule excludes genuine methods; that exclusion does not exclude card-015's method-as-field case

<a id="merged-field-projection-before-apply"></a>
## Parenthesize spec-function-valued field projection before application

Source cards: card-060, card-075

**Trigger:**
- Verus compile errors say a struct field is not a method when a stored spec function is applied directly to an argument in a proof.
- Verus emits a compile error saying a public spec-function-valued field has no method with that name when it is used with call-like dot syntax.

**Action:**
- Treat the projection as a field access; parenthesize the field projection before applying it to the argument, and repeat the correction for each occurrence of the pattern.
- After fixing parsing, if Verus reports a missing trigger for the universal equality, add explicit trigger annotations to both sides of the equality.
- Especially repeat the same parenthesized field application inside quantified equality reasoning and forward-propagation steps.

**Why:**
- The field stores a function value, not a method, so the projection must be parenthesized before it is applied to be treated as a callable value.
- The explicit trigger lets the pointwise equality quantifier instantiate at arbitrary indices so the execution equality lemma can be applied.
- Otherwise the compiler resolves the projection as a nonexistent method call and aborts before proof checking.

**Validate:**
- Re-run Verus; the compile errors should disappear or vanish.
- If a subsequent trigger error appears, adding the explicit trigger should enable verification; the final proof should pass with all proof functions verified and the safety comparison clean.
- Subsequent proof diagnostics such as precondition, postcondition, or quantifier failures may appear; do not stop until those proof goals and Lynette pass.

**Avoid when:**
- Do not apply when the field is not a function-valued field, or the equality can be proved by another supplied lemma without pointwise expansion; fixing syntax does not replace a missing logical fact.
- Do not apply when the projection is genuinely a declared method rather than a function-valued field, or the expression is an actual method call rather than a field application.

**Version scope:**
- No explicit Verus version scope is stated in either source card.


- Distinguish from [record-function-field-equality](record-function-field-equality.md): This route corrects projection/application syntax only; it does not establish pointwise equality or record equality.

- Related [record-function-field-equality](record-function-field-equality.md): This family corrects projection/application syntax only; record-function-field-equality establishes logical field and record equality after the syntax is corrected.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Card-060 and card-028 include a conditional follow-up to add explicit triggers for universal pointwise equality after syntax repair; trigger-inference-annotation handles standalone trigger-inference failures without the initial field-call parse error.

- Related [quantified-proof-antecedent-binder-scope](quantified-proof-antecedent-binder-scope.md): The second branch of verbatim card-015 overlaps with quantified-proof-antecedent-binder-scope's missing-antecedent repair. It remains inside the verbatim rule because the source card bundles both diagnostics.

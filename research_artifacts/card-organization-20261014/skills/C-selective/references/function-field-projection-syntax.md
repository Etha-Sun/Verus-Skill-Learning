# Function-valued field versus method access

## Scope

- Consult when: A method is mistaken for a field, a stored function field is called as a method, or pointwise record equality has the related syntax/trigger failure
- Consult when: Card-015's separate case matches a quantified-proof missing-antecedent diagnostic
- Not for: None of these method/field, pointwise-equality trigger, or missing-antecedent diagnostics is present
- Boundary: The stored-function rule excludes genuine methods; that exclusion does not exclude card-015's method-as-field case

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 015 covers both method/field directions and a separate antecedent diagnosis; 028 focuses on pointwise record equality; the merged rule focuses on stored-function field calls. Field-call and later trigger cases overlap. These are reading focuses, not exclusive eligibility tests.

<a id="card-015-verbatim"></a>
- [card-015-verbatim](function-field-projection-syntax--card-015-verbatim.md): Method/field classification or separate antecedent issue.
  - When: A method is treated as a field, a function field as a method, or a quantified proof lacks its implication antecedent.
  - Avoid: Neither method/field nor antecedent diagnostic is present; implication syntax is version-sensitive.

<a id="card-028-verbatim"></a>
- [card-028-verbatim](function-field-projection-syntax--card-028-verbatim.md): Pointwise record equality with function-field diagnostics.
  - When: The failing proof is pointwise record equality and has field-call syntax or uninferred equality-trigger diagnostics.
  - Avoid: Treating pointwise agreement as field/record equality before the original rule's field-equality obligation is met.

<a id="merged-field-projection-before-apply"></a>
- [merged-field-projection-before-apply](function-field-projection-syntax--merged-field-projection-before-apply.md): Stored spec-function field called as a method.
  - When: A compile error reports no method for a function-valued field used with call-like dot syntax.
  - Avoid: A genuine method, a non-function field, or a missing logical fact.

Read: `python3 reference_read.py function-field-projection-syntax --rules ID [ID ...]`

Whole reference: `python3 reference_read.py function-field-projection-syntax --full` or [function-field-projection-syntax--full.md](function-field-projection-syntax--full.md).

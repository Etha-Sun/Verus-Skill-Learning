# Record equality with function-valued fields

## Scope

- Consult when: Goal is equality of records containing function-valued projection fields
- Consult when: Pointwise premise is available or built-in extensional equality is needed
- Not for: Pointwise premise is incomplete
- Not for: No function-valued field is involved

<a id="rule-card-005"></a>
## Verbatim card-005

Source cards: card-005

**Trigger:** The same pointwise function-equality premise is available, but a direct equality assertion on the function values is not discharged by the verifier, and helper names for function equality are unavailable or rejected.

**Action:** Use the built-in extensional equality relation available from the standard prelude on the two function-valued fields inside a proof assertion. Remove unavailable imports or unsupported helper calls and rerun.

**Why:** The built-in extensional equality relation is the supported way to expose equality of function values from pointwise agreement. Once the fields are known equal by that relation, structural equality of the containing record follows.

**Validate:** Run Verus and expect zero errors. Then run the safety comparison tool; both should pass.

**Avoid when:** The extensional equality relation is not available in the installed prelude, or the premise is not complete pointwise agreement. Do not add a new axiom or import from a non-existent module as a workaround.

## Conditional links

- When After syntax and triggers are fixed, when the remaining proof uses pointwise function-field equality to derive execution equality.: [function-field-projection-syntax/merged-field-projection-before-apply](function-field-projection-syntax.md#merged-field-projection-before-apply)
- When After the syntax and trigger are fixed, when the remaining proof step is asserting function-field and record equality.: [function-field-projection-syntax/card-028-verbatim](function-field-projection-syntax.md#card-028-verbatim)

- Distinguish from [function-field-projection-syntax](function-field-projection-syntax.md): Syntax route fixes callable-field parse/type errors; this route establishes logical field and record equality after syntax is correct.

- Related [function-field-projection-syntax](function-field-projection-syntax.md): Syntax route fixes callable-field parse/type errors; this route establishes logical field and record equality after syntax is correct.

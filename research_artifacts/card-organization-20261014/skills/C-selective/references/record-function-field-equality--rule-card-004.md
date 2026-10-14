# Record equality with function-valued fields

## Scope

- Consult when: Goal is equality of records containing function-valued projection fields
- Consult when: Pointwise premise is available or built-in extensional equality is needed
- Not for: Pointwise premise is incomplete
- Not for: No function-valued field is involved

<a id="rule-card-004"></a>
## Verbatim card-004

Source cards: card-004

**Trigger:** A proof function has an empty or incomplete body and its postcondition is equality of two records that contain a function-valued projection field; a premise already gives pointwise equality of that projection for every index. Verus reports only the postcondition unsatisfied.

**Action:** Add a proof-only local assertion for equality of the function-valued projection fields. If the proof style prefers making the next step explicit, also assert equality of the whole record afterward. Do not change the function signature, premise, or executable behavior.

**Why:** Verus can justify equality of the function-valued field from the pointwise quantified premise, and record equality then follows from equality of the component fields. This closes the structural equality obligation without introducing assumptions or weakening the specification.

**Validate:** Run Verus and expect the function to verify with zero errors. Then run the safety comparison tool to confirm the edit is proof-only.

**Avoid when:** The premise gives equality only for a subset of indices, or the records have other fields that are not known equal. Do not assert field equality unless the full pointwise premise actually covers it.

## Conditional links

- When After syntax and triggers are fixed, when the remaining proof uses pointwise function-field equality to derive execution equality.: [function-field-projection-syntax/merged-field-projection-before-apply](function-field-projection-syntax.md#merged-field-projection-before-apply)
- When After the syntax and trigger are fixed, when the remaining proof step is asserting function-field and record equality.: [function-field-projection-syntax/card-028-verbatim](function-field-projection-syntax.md#card-028-verbatim)

- Distinguish from [function-field-projection-syntax](function-field-projection-syntax.md): Syntax route fixes callable-field parse/type errors; this route establishes logical field and record equality after syntax is correct.

- Related [function-field-projection-syntax](function-field-projection-syntax.md): Syntax route fixes callable-field parse/type errors; this route establishes logical field and record equality after syntax is correct.

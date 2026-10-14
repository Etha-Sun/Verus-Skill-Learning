# Specialized temporal action binder payload type

## Scope

- Consult when: A fairness/action is specialized to a fixed controller or identifier
- Consult when: Universal binder uses full action-input tuple and Verus reports a payload type mismatch
- Not for: The error points to a different action
- Not for: The action's declared input type or fixed argument should not change

## Rules

- [Specialized temporal action binder payload type](#specialized-temporal-action-binder-type)

<a id="specialized-temporal-action-binder-type"></a>
## Specialized temporal action binder payload type

Source cards: card-027

**Trigger:** While proving stability for a fairness obligation whose action has already been specialized to a fixed controller or identifier, the verifier reports mismatched types in a universal quantifier, expecting a payload type but the binder uses the full action-input tuple.
**Action:** Change those universal binders to range only over the remaining payload type. Keep the fixed identifier or key inside the action call. Update all corresponding predicate variables and conjunction-stability arguments to use that same payload type consistently.
**Why:** After the action input is partially applied to the fixed identifier, only the residual payload is universally quantified. Using the full tuple creates a nested tuple and a type mismatch, whereas the payload-only binder matches the action's input type.
**Validate:** Run the verifier after the type correction. In the observed branch, this eliminated all mismatched-type errors and allowed the existing stability proof to finish with zero errors; the final candidate passed both checks.
**Avoid when:** Avoid changing the action's declared input type or the fixed argument itself. If the error points to a different action, determine that action's residual input type before editing; a type correction here is only for the specialized fairness binders, not a general assertion.

- Distinguish from [function-field-projection-syntax](function-field-projection-syntax.md): Function-field route fixes field-call syntax; this route fixes the residual universally quantified payload type after partial action application.

- Related [function-field-projection-syntax](function-field-projection-syntax.md): Function-field route fixes field-call syntax; this route fixes the residual universally quantified payload type after partial action application.

- Related [natural-integer-type-mismatch](natural-integer-type-mismatch.md): Specialized binder route fixes a partial-application residual payload type; this route handles natural/integer numeric and empty-sequence types.

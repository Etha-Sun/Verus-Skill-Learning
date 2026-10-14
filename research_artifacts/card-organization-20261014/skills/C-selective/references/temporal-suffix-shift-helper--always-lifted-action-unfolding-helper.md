# Temporal always/suffix goals via existing shift or unfolding helpers

## Scope

- Consult when: Goal is a suffix-wise or always-derived property
- Consult when: An existing accepted unfolding/shift helper matches the available premise
- Consult when: Satisfaction, always, lifting, head, and next-state definitions are open enough
- Not for: Helper is absent or would require a new trusted body
- Not for: Current assumption does not match helper precondition

<a id="always-lifted-action-unfolding-helper"></a>
## Always-lifted action premise unfolded to suffix-wise satisfaction via existing helper

Source cards: card-025

**Trigger:** A proof obligation requires a property to hold at every suffix of an execution, and the available premise states that an always-form of a lifted action is satisfied by that execution. An existing proof helper already unfolds the always form into suffix-wise satisfaction.
**Action:** Invoke the existing unfolding helper with the current execution and the wrapped temporal predicate; supply explicit type arguments if the wrapped predicate is not inferred. Rely on the open definitions of lifting, satisfaction, head, and next-state to reduce suffix satisfaction to the underlying action on the first two states.
**Why:** The helper converts the premise into a universal fact over suffix indices; open definitions then expose exactly the action-level conclusion, avoiding a duplicated quantifier proof.
**Validate:** Run the verifier after the proof-body edit. In all four observed branches of the small task, this changed a postcondition failure to one verified function with zero errors, and the proof-only safety comparison passed.
**Avoid when:** Avoid if the unfolding helper is not already accepted by the verifier without introducing a new trusted body; if it is absent or does not discharge, prove the suffix expansion directly instead of adding an assumption or weakening the postcondition.

- Distinguish from [temporal-induction-natural-offset](temporal-induction-natural-offset.md): This route applies an existing helper; induction route constructs a recursive proof over a natural offset.

- Related [temporal-induction-natural-offset](temporal-induction-natural-offset.md): This route applies an existing helper; induction route constructs a recursive proof over a natural offset.

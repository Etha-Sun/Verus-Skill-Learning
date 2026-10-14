# Temporal always/suffix goals via existing shift or unfolding helpers

## Scope

- Consult when: Goal is a suffix-wise or always-derived property
- Consult when: An existing accepted unfolding/shift helper matches the available premise
- Consult when: Satisfaction, always, lifting, head, and next-state definitions are open enough
- Not for: Helper is absent or would require a new trusted body
- Not for: Current assumption does not match helper precondition

## Rules

- [Nested always postcondition via existing forward-shift helper](#nested-always-forward-shift-helper)
- [Always-lifted action premise unfolded to suffix-wise satisfaction via existing helper](#always-lifted-action-unfolding-helper)

<a id="nested-always-forward-shift-helper"></a>
## Nested always postcondition via existing forward-shift helper

Source cards: card-014

**Trigger:** A proof function must establish a nested always property of an execution, the body is empty, and the surrounding rules define a helper that shifts an always guarantee to any suffix of the execution.

**Action:** Use the open definitions of the satisfaction and always functions to view the goal as a universal statement over natural suffix indices. Assert that universal statement, and for an arbitrary index invoke the existing forward-shift helper using the current assumption to prove the shifted suffix satisfies the inner property.

**Why:** The nested always postcondition unfolds structurally into exactly the universal suffix claim. The provided forward-shift rule has the same precondition as the current proof and produces the needed conclusion for every index, so no manual lambda reasoning or new definitional equality is required.

**Validate:** Run the Verus checker and expect all proof functions to verify with zero errors; run the proof-safety comparison tool and require exit zero.

**Avoid when:** The necessary forward-shift helper is not present, the satisfaction and always functions are not open enough to unfold automatically, or the current assumption is not exactly the helper's required assumption.

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

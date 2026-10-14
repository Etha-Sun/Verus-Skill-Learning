# Temporal always/suffix goals via existing shift or unfolding helpers

## Scope

- Consult when: Goal is a suffix-wise or always-derived property
- Consult when: An existing accepted unfolding/shift helper matches the available premise
- Consult when: Satisfaction, always, lifting, head, and next-state definitions are open enough
- Not for: Helper is absent or would require a new trusted body
- Not for: Current assumption does not match helper precondition

<a id="nested-always-forward-shift-helper"></a>
## Nested always postcondition via existing forward-shift helper

Source cards: card-014

**Trigger:** A proof function must establish a nested always property of an execution, the body is empty, and the surrounding rules define a helper that shifts an always guarantee to any suffix of the execution.

**Action:** Use the open definitions of the satisfaction and always functions to view the goal as a universal statement over natural suffix indices. Assert that universal statement, and for an arbitrary index invoke the existing forward-shift helper using the current assumption to prove the shifted suffix satisfies the inner property.

**Why:** The nested always postcondition unfolds structurally into exactly the universal suffix claim. The provided forward-shift rule has the same precondition as the current proof and produces the needed conclusion for every index, so no manual lambda reasoning or new definitional equality is required.

**Validate:** Run the Verus checker and expect all proof functions to verify with zero errors; run the proof-safety comparison tool and require exit zero.

**Avoid when:** The necessary forward-shift helper is not present, the satisfaction and always functions are not open enough to unfold automatically, or the current assumption is not exactly the helper's required assumption.

- Distinguish from [temporal-induction-natural-offset](temporal-induction-natural-offset.md): This route applies an existing helper; induction route constructs a recursive proof over a natural offset.

- Related [temporal-induction-natural-offset](temporal-induction-natural-offset.md): This route applies an existing helper; induction route constructs a recursive proof over a natural offset.

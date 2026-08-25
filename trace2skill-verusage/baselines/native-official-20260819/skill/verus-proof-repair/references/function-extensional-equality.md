# Function Extensional Equality

## When to use

A struct equality obligation depends on equality of a function field, and a pointwise equality assumption about those functions is visible.

## Pattern

1. Ensure the pointwise equality assumption is quantified and annotate the equality with `#[trigger]`:
   `forall |i: nat| #[trigger] (f)(i) == (g)(i)`
2. In the proof body, assert extensional equality with Verus's built-in operator:
   `assert(f =~= g);`
3. Let Verus derive `f == g`; structural equality for the enclosing struct then follows.

## Notes

- Prefer this single targeted assertion over macro-based proof attempts for this obligation.
- Use only visible facts; do not add assumptions or weaken contracts.

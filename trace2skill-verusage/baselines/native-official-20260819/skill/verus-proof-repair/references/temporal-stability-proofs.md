# Temporal Stability Proof Patterns

Use when a Verus temporal invariant stability obligation arises and the target invariant is a conjunction of `always` subpredicates, or the goal is `valid(stable(S.and(T)))` or another stable-conjunction/bounded-universal stability postcondition.

## Reproduce and preserve the original

1. Reproduce the exact Verus diagnostic before editing: run Verus on the target file, or inspect its existing log as secondary evidence.
2. Preserve the original benchmark file. If the original must remain unchanged, copy it to `<name>_verified.rs` and work in that copy only when that artifact is the assigned proof target; otherwise apply the final proof annotations back to the original target.

## Structural decomposition first

Before selecting a tactic, expand the target invariant and classify its logical structure. In a successful proof, recognizing that `invariants_since_phase_ii` was exactly a conjunction of three `always(lift_state(...))` predicates made the existing macro applicable immediately.

## Pattern: `stable_and_always_n` / one-shot macro path

If the repository defines `stable_and_always_n`, use it directly.

1. Confirm the macro's expected shape: a conjunction of `n` `always(p)` predicates.
2. Locate the existing component proofs that each `always(p)` is stable.
3. Pass those component proofs to the macro instead of writing manual assertion chains.

```rust
// Illustration: conjunction of three always predicates
proof {
    stable_and_always_n!(
        invariants_since_phase_ii,
        component_stability_1,
        component_stability_2,
        component_stability_3
    );
}
```

Do not recreate the conjunction stability proof by hand when this macro already exists.

## Stable conjunction (`stable_and_temp`)

1. Prove the stable half first. For example, call the base stability lemma `stable_spec_is_stable(cluster, controller_id)` to obtain `valid(stable(stable_spec(cluster, controller_id)))`.
2. Apply `stable_and_temp(S, T)` to combine that stable fact with the temporal part `T`.
3. Repeat for each conjunct, such as `stable_spec(...).and(invariants(...))`.

Do not manually unfold the temporal stability definitions when these lemmas already compose the proof.

## Bounded universal stability postcondition

Use an in-proof `assert forall ... by` block rather than a separate case analysis:

```rust
assert forall |i: nat| 0 <= i <= 5 implies <stability property for i> by {
  // call stable_and_temp or the appropriate per-index helper, e.g. on spec_before_phase_n(i, ...)
}
```

This discharges the bounded universal postcondition for all required indices at once.

## Manual per-conjunct path

If the one-shot macro is not available or the conjunction does not close, prove each conjunct separately and then combine.

1. For each conjunct, prove its individual stability:
   ```rust
   always_p_is_stable(lift_state(<conjunct expression>));
   ```
2. Close the conjunction with the existing stability-conjunction macro:
   ```rust
   stable_and_n![
       always(lift_state(Cluster::...)),
       always(tla_forall(...)),
       ...
   ];
   ```
3. Mirror the exact syntax of the target predicate in the macro arguments. List each `always(...)` and `lift_state(...)` expression exactly as it appears in the target definition.
4. Run Verus on the assigned target. Finish only after that fresh run succeeds.

## Warnings

- Do not manually reason over the entire conjunction; prove each conjunct individually and combine.
- Do not simplify or rewrite conjunct syntax before passing it to a stability macro; use the exact target syntax.
- Do not infer success from a smaller error count; require a clean Verus run.
- Do not use a separate `<name>_verified.rs` copy as a substitute for verifying the assigned original path unless that copy is the assigned proof target.

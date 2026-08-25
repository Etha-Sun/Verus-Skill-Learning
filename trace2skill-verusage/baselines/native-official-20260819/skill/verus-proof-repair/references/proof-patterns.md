# Verus Proof Patterns

Observed successful patterns for recurring proof obligations. Read only the section matching the current Verus diagnostic or goal.

## Resolve macro/environment failures before proof work

Use when a target is a standalone file with `verus!`-dependent macros, reports unavailable `builtin_macros` or generated-code failures, parser errors, or macro-delimiter errors. Do not attack proof obligations until these are resolved.

- Inspect and use the project's macro-expansion script or equivalent first.
- Delete or replace broken `macro_rules!` definitions or invocations such as `define_enum_and_derive_marshalable!`, `marshalable_by_bijection!`, and `derive_marshalable_for_*!`.
- For macro-generated `Marshalable` compile failures, replace problematic derive/bijection-style marshalability macro invocations with explicit `impl Marshalable` blocks for each enum or struct, then remove the macro definitions. This avoids nested `builtin::verus!` resolution issues and exposes the next real proof obligation.
- Write explicit type definitions plus `open spec fn is_marshalable` and `ghost_serialize` impls where needed.
- Use exact line-range or targeted text replacement so the edit removes parser/macro errors and exposes only actual verification obligations.
- Rerun Verus so diagnostics reveal only real proof obligations.

## Construct explicit ghost witnesses, not `arbitrary()`

For ghost-return functions or constructor/init specs with strong postconditions, initialize ghost variables with the exact value the postcondition or invariant requires rather than `arbitrary()`.

- Use exact initial values such as `Seq::<T>::empty()`, an empty map, or `None`.
- If a later equality requires `x == Seq::<T>::empty()`, initialize `x` to `Seq::<T>::empty()` before constructing the concrete state.
- Invoke any proof lemma in a `proof` block after constructing the witness.

```rust
let result = EventResults { /* all fields Seq::empty() */ };
proof {
    lemma_empty_ios_extract_packets();
}
result
```

## Prove large init postconditions in layers

For complex `init_ensures`/invariant obligations, do not write one monolithic assertion.

1. Construct the concrete state first.
2. Add separate `proof {}` blocks to:
   - assert facts from called constructors or helper functions;
   - prove concrete-state invariants and validity;
   - prove the abstract init spec by field-by-field abstract equality;
   - assert every conjunct of the final `init_ensures` explicitly.
3. Use each changed diagnostic to close one layer at a time.

## Prove empty-container pipelines by direct stepwise equality

For goals involving chains of map/filter/to_set extensions on empty collections, assert each intermediate empty result explicitly. This gives Verus a concrete step-by-step equality path and avoids broad or incorrect generic lemma signatures.

```rust
assert(abstractify_raw_log_to_ios(Seq::empty()) == Seq::empty());
assert(empty.filter(...) == Seq::empty());
assert(empty.map(...) == Seq::empty());
assert(empty.to_set() == Set::empty());
```

## Bidirectional equality / iff

When the unproved goal is `A <==> B` or `s1 == s2 <==> expr1 == expr2`, prove each direction separately.

- Forward direction (`left ==> right`): assume the left equality and prove the right by substitution. This is often automatic.
- Backward direction (`right ==> left`): if sequences are involved, derive equal lengths from the equal concatenated expressions, then prove pointwise equality at an arbitrary index and close with extensional equality (`=~=`).

## Postcondition about a function argument fails after a loop

Trigger: a loop body verifies, but a postcondition mentioning `old(arg)` remains unproved.

Add loop invariants that mention `old(arg)` explicitly, tying current state to the function's original state. Example: `netc.my_end_point() == old(netc).my_end_point()` and `old_history == old(netc).history()`. Local snapshot variables alone are not enough.

## Early failure return with `forall` over an output sequence

Trigger: an early failure return must satisfy a quantified postcondition such as `forall|i| 0 <= i < seq.len() ==> seq[i] is Send`.

Return `Seq::empty()` instead of `arbitrary()` for the ghost output sequence. This makes the quantified sequence postcondition hold vacuously when no events are produced.

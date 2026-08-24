# State-Machine Invariant Proofs

Read this when the unproved obligation is a temporal invariant such as
`always(lift_state(P))`, or when preservation of a state/message invariant across
a transition fails.

## 1. Convert the temporal goal with `init_invariant`

Define the invariant locally and prove two one-step obligations:

```rust
let inv = |s: State| /* P lifted over s */;

assert forall |s: State| init(s) implies inv(s) by {
  // initial-state reasoning
}

assert forall |s: State, s_prime: State| inv(s) && next(s, s_prime) implies inv(s_prime) by {
  // transition reasoning
}

init_invariant::<State>(spec, init, next, inv);
```

This reduces `always(lift_state(P))` to ordinary verification conditions.

## 2. Make message-set invariants solver-friendly

When the invariant quantifies over in-flight messages, assert the property
directly over the new state's in-flight set:

```rust
assert forall |msg: Message|
  #[trigger] s_prime.in_flight().contains(msg) && /* msg conditions */
  implies /* desired property */
by {
  // ...
}
```

In the transition case, branch on `s.in_flight().contains(msg)`:
- old messages follow from `inv(s)`;
- new messages follow from transition/model definitions.

## 3. Inspect model-generating definitions before expanding cases

Before manually enumerating transition cases, search for the definitions that
generate next-state messages or requests. Facts such as `external_model: None`
or a generator returning only one request kind can close new-message branches
directly, avoiding unnecessary case splits.

# Set Proof Patterns

Use these patterns when a `Set` equality, set/map membership, sorted no-duplicate set-removal goal, recursive finite-set property, or finite-set fold/map equality does not verify.

## General `Set` equality and map membership

1. Write the high-level assertion first and run Verus to confirm it is not automatic.
2. Replace the high-level set equality with two directed membership implications:

   ```verus
   assert(forall |b| #[trigger] lhs.contains(b) ==> rhs.contains(b));
   assert(forall |b| #[trigger] rhs.contains(b) ==> lhs.contains(b));
   assert(lhs =~= rhs);
   ```

   The two `forall` assertions give the SMT solver both containment directions needed for set extensionality.

3. For `s.map(f).contains(b)`, introduce a chosen preimage and assert every witness fact explicitly:

   ```verus
   let a = choose |a: A| s.contains(a) && #[trigger] f(a) == b;
   assert(s.contains(a));
   assert(f(a) == b);
   // assert map-membership fact as needed
   ```

4. If the set is formed by a union, case-split on whether the witness belongs to one side or the other:

   ```verus
   if s1.contains(a) { ... } else { ... }
   ```

   This lets Verus connect union and map membership automatically.

5. Close with the original equality/high-level goal and run a fresh full-file Verus check.

## Sorted no-duplicate sequence: set equality after removal

Trigger: proving `old_set.minus(removed) == new_set` for a sorted no-duplicate sequence after removing an element.

Use bidirectional set inclusion:

1. Show every element in the new set is in the old set and not equal to the removed element.
2. Show every element in `old_set.minus(removed)` is in the new set.

Key facts Verus needs visible at the obligation:

- Membership in the new sequence comes from an old index different from the removed index.
- No duplicates in the old sequence prevent the same value from appearing at multiple positions.

## Recursive finite-set property: induction with size

For a recursive property over finite sets (e.g. `map_fold(s, f).finite()` from `s.finite()`):

- State the lemma's termination measure as `decreases s.len()`.
- Split into `s.is_empty()` and `!s.is_empty()` cases.
- Empty case: finish directly from the definition.
- Nonempty case: choose an arbitrary element `x` with `s.contains(x)`; apply the induction hypothesis to `s.remove(x)`; reconstruct the original set by inserting `x`; use the local fact that insertion preserves the property. Avoid expanding the whole set operation.

## Finite-set fold/map equality

Use for `map_fold(s, f) == s.map(f)` or similar recursive finite-set fold equality.

1. Prove by induction on the finite set size. State `decreases s.len()` on the lemma or proof function.
2. Split into empty and nonempty cases.
   - Empty: simplify the fold and map; the equality closes by definition.
   - Nonempty: choose an element `a` of `s`.
3. Apply the inductive hypothesis to `s.remove(a)`.
4. Connect the result to the full set:
   - The fold over `s` is the fold over `s.remove(a)` extended with `f(a)`.
   - The map over `s` is `s.remove(a).map(f)` extended with `f(a)` via `insert(f(a))`.
5. Prove the inserted-element set equality element-wise by bidirectional containment:
   - Show every element of the left set is either `f(a)` or belongs to the smaller map.
   - Show every element of the right set is either `f(a)` or belongs to the smaller map.

Use explicit `assert forall` assertions for the two containments. This gives Verus the explicit mutual containment proof instead of leaving the set equality opaque.

## Safety

Do not add `assume`, `admit`, `external_body`, axioms, or verification bypasses when these direct assertions fail. If the pattern does not apply, return to the core workflow and choose the next smallest proof change. After applying this pattern, rerun Verus and confirm zero errors.

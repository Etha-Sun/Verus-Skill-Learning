# Verus Proof Patterns

This reference collects proven, minimal‑action techniques for recurring Verus obligations. Use a pattern only when its trigger exactly matches the current error or goal.

## Loop Break Proof Patterns

**Trigger:** A postcondition depends on whether a loop exited via `break`.

**Pattern:**
1. Declare a ghost variable (e.g., `let ghost mut broke_at: Option<nat> = None;`) and set it inside the break branch.
2. Maintain an invariant linking the ghost variable to the loop state:
   ```rust
   invariant
       broke_at.is_none() || (broke_at == Some(i) && some_condition(i))
   ```
3. Do not attempt to re‑evaluate the break condition after the loop.
4. If invariants become too complex, restructure the loop to carry a flag that is easier to track.

## Loop Proof Patterns (bounds, subranges, pushes)

**Decreases clause:** Every `while` loop needs a decreases clause, e.g., `decreases N - i`.

**Slice indexing:** Add invariants connecting the loop index to the slice length: `s@.len() == len`, `0 <= i < len`.

**Vec push subrange reasoning:** After `push`, assert subrange equalities to maintain invariants:
```rust
assert(data@.subrange(original_len as int, data@.len() as int) ==
       spec_seq.subrange(0, i as int).push(spec_seq[i as int]));
```
Break into smaller steps (`subrange` extension, old length equality) if necessary.

**Quantified loop invariants:** Use `#![auto]` inside quantifiers to let Verus choose triggers.

## Set Equality and Induction

**Set equality via extensionality:**
```rust
assert(forall |y: A| left_set.contains(y) == right_set.contains(y) by {
    // prove both directions
});
assert(left_set =~= right_set);
```
For `Seq::push` vs `Set::insert`, use mutual containment with `choose` to extract witnesses.

**Set induction:**
- Add `decreases s.len()` for termination.
- Case split on `s == Set::empty()` vs arbitrary `x = s.choose()`, `s.remove(x)`, and apply induction hypothesis.
- Prove finiteness of composite sets by breaking into sub‑expressions and using lemmas like `finite_set_insert`.

## Universal Quantifiers

**Trigger:** Postcondition is `forall|x: T| ...` and unproven.

**Pattern:** Wrap the proof body in `assert forall|x: T| ... by { ... }`. The inner block proves the property for an arbitrary `x`; Verus lifts it.

**Instantiation:** If a lemma already proves the property for concrete arguments, use:
```rust
assert forall(|param1, param2| lemma_name(param1, param2));
```

**Trigger warnings:** Use `#![auto]` before the range condition to suppress “no trigger” warnings when the assertion is already sound.

## Trait Implementation and Serialization Proofs

- Never redeclare trait contracts in impl methods; rely on inherited specs.
- Use ghost snapshots (`let ghost old_self = *self;`) to relate pre‑state to post‑state.
- For cumulative serialization (e.g., sequential calls that append), use subrange assertions to show concatenation equals `ghost_serialize()`.

## Induction and Definition Inspection

**Trigger:** A recursive function is opaque and induction fails.

- Use `assert(expr == expected) by(compute_only);` to reveal the function’s definition.
- Match the induction case split to the function’s actual recursion (e.g., right‑to‑left for `drop_last`/`last`).
- For `fold_left`, do not attempt a prefix‑suffix decomposition that cannot be proved; prefer simple index‑based induction.

## Lemma Induction Strategies

- Avoid introducing lemmas whose body cannot be proved immediately; verify them in isolation before calling.
- If a decomposition of `fold_left` repeatedly fails, abandon it and use element‑by‑element induction.
- When stuck after three attempts, redesign the proof with a simpler recurrence.
- Check existing vstd theorems before encoding new algebraic properties.

## Composite Types and Delegation

**Trigger:** A proof obligation involves a composite type (tuple, struct) whose fields already have proven lemmas.

**Pattern:** Call the per‑field lemmas instead of repeating the proof:
```rust
self.field.lemma_same_views_serialize_the_same(&other.field);
```
Combine the results to prove the top‑level obligation.

## Proof Annotation and Macro Handling

- **Replace `arbitrary()`** with concrete expressions; add a proof block to connect to specs.
- **Fix deprecation warnings**: use `is None` instead of `is_None()`.
- **Macro expansion fallback**: When built‑in macros are unavailable (e.g., `::builtin_macros::verus!`), manually expand them and verify the expansion with Verus immediately before making proof changes. Never expand complex macros like `define_enum_and_derive_marshalable!` unless absolutely necessary.

## Vector and Sequence Patterns

- **Ghost snapshots**: capture `data@` before mutations, and assert subrange equalities after each update.
- **Seq equality**: use extensional equality (`s =~= t`) after proving element‑wise equality.
- **View coercions**: use `@` in invariants/assertions to align concrete and abstract values.

## Ordering and Sorted Maps

- **Comparator transitivity**: Inside proofs that depend on `lt_spec`, call `K::cmp_properties()` first.
- **Gap lemmas**: For sorted keys, prove no key lies between adjacent indices by using sortedness and index‑ordering lemmas.

## Quantifier Trigger and Instantiation

- **Suppress warnings**: Annotate the intended trigger with `#[trigger]`.
- **Explicit witness**: For subset proofs, reuse the forall‑bound variable as the existential witness.
- **Single‑quote variables**: In Rust 2021 closures, rename parameters with single quotes to plain identifiers.

## Miscellaneous

- **Option/Result branching**: Split ensures into `if opt is Some { ... } else { ... }` to avoid unwrap on None.
- **Well‑typedness**: Prove zero‑length for empty fields and a `forall` over elements.
- **Full‑file verification**: After macro expansion or adding helper lemmas, run Verus on the whole file, not just the target function.

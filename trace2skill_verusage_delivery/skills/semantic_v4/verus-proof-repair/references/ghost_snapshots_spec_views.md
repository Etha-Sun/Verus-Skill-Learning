# Ghost Snapshots, Spec Views, and Concrete-to-Abstract Equality

**Consult when:** Proof blocks need @-views, stable let ghost snapshots, replacement of arbitrary ghost placeholders, Ghost return placement, or chains from concrete fields/views to abstract specs.

**Do not consult when:** The main issue is loop invariant design or recursive sequence recurrence rather than concrete/ghost typing and view chain scaffolding.

<a id="verus-global-034"></a>

## verus_global_034 — Bind inline results and ghosts to named lets for stable triggers and ensures

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** An assertion, quantifier, or later proof block must refer to an inline function result, a sequence expression, or a ghost snapshot, but the term is unnamed or proof-block scoped.

**Obstacle:** Inline expressions do not carry function ensures clauses cleanly into assertions; repeated sequence expressions can be trigger-unstable; proof-block-local ghost bindings are not visible outside that block.

**Mechanism:** Introduce an immutable named `let` or `let ghost` binding at the earliest enclosing scope where the term must be reused, then refer only to that bound name in later proof blocks and assertions.

**Procedure:**
1. Identify the inline value, function result, sequence expression, or ghost view whose equality or trigger is required.
2. Bind it with `let` or `let ghost` before the first proof block or assertion that needs it.
3. If the binding must survive multiple proof blocks, declare it at function-body scope rather than inside a `proof` block.
4. Reference only the bound name in subsequent assertions and quantifier triggers.

**Why:** A named term gives Verus a stable trigger and carries postconditions or spec equalities, avoiding repeated trigger matching and scope loss.

**Check:** Later proof blocks and assertions use the named binding rather than recomputing the inline expression; no cross-block reference relies on a proof-local ghost.

**Avoid or stop:**
- Do not use a proof-block-local ghost when later blocks need it.
- Do not bind irrelevant values.

<a id="verus-global-035"></a>

## verus_global_035 — Expose spec-view sequence values with @ for proof indexing and length reasoning

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A proof or ghost block must index or reason about lengths and elements of a concrete collection, or it currently uses executable indexing inside `proof`.

**Obstacle:** Executable indexing is ill-typed inside proof or ghost code; the solver needs the sequence view (`Seq<T>`) for length, indexing, and quantifier reasoning.

**Mechanism:** Coerce concrete collections to spec views with `@`, bind those views to local names if repeated access is needed, and use spec-view indexing for all ghost-only reasoning.

**Procedure:**
1. Inside ghost or proof code, use the spec-view operator `@` to turn the concrete collection into a sequence value.
2. Bind the view to a local name if repeated length or element access is needed.
3. Replace executable indexing with spec indexing, such as `collection@[i as int]`.
4. Use the bound sequence view for `len()`, element access, and quantifier bodies.

**Why:** Spec-view indexing and length operations fit ghost-only reasoning and align with spec definitions that quantify over views.

**Check:** All ghost and proof indexing uses `@` or a bound spec-sequence view; no executable collection indexing remains inside a proof block.

**Avoid or stop:**
- Do not use executable-view indexing in ghost or proof code.
- Ensure integer casts match Verus sequence index types where required.

<a id="verus-global-036"></a>

## verus_global_036 — Chain concrete fields, abstract snapshots, and spec-view equalities to satisfy view postconditions

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A postcondition equates a concrete value or structure with an abstract spec function over a view; the relation is not direct, and invariants may recur over a collection.

**Obstacle:** Concrete representation and abstract view differ; the solver cannot align a concrete field or value to an abstract spec function without intermediate equalities.

**Mechanism:** Compose three stages: bind a stable ghost abstraction of the immutable abstract input; expose concrete collection elements or fields through `@` views; chain equality from concrete field or view to the spec-function result.

**Procedure:**
1. Bind an immutable abstract snapshot of the input before the loop or main reasoning.
2. Carry an invariant that the snapshot equals the concrete input abstraction so later elements can refer to a stable value.
3. Inside the invariant and assertions, expose the concrete element view with `@` rather than using the concrete object directly.
4. Compare that view against the spec-function result on the abstract snapshot.
5. For final equality, decompose into simple equalities: function result view, field equality, struct view equality, and final abstract view equality.

**Why:** Named abstract snapshots and explicit view coercions make the bridge from concrete to spec explicit, enabling transparent chains instead of one large equality.

**Check:** Each assertion connects exactly one concrete, field, or view level to the next; the final postcondition follows from the composed equalities.

**Avoid or stop:**
- Do not mix concrete objects and their views in the same equality without exposing `@`.
- Avoid using an abstraction snapshot without carrying an invariant that it equals the current input abstraction.

<a id="verus-global-037"></a>

## verus_global_037 — Replace arbitrary ghost placeholders with concrete values and bridge to specs in proof blocks

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A ghost variable or return value is initialized with `arbitrary()` and postconditions about it are unprovable, or an already computed concrete result needs to be connected to an abstract specification.

**Obstacle:** `arbitrary()` provides no information about the actual value, so the verifier cannot prove structural or spec equality postconditions.

**Mechanism:** Substitute the exact concrete value guaranteed or computed by preceding code, or construct concrete struct fields explicitly; then add small proof-block assertions linking the concrete value or fields to the abstract postcondition.

**Procedure:**
1. Identify whether the ghost variable or placeholder corresponds to a concrete value already determined by the code.
2. Replace `arbitrary()` with that exact expression or with an explicit construction of the concrete value.
3. In a `proof { ... }` block, assert the one-step facts that connect the concrete expression or fields to the spec view or function mentioned in the postcondition.
4. Let Verus propagate the established equality through the conclusion; avoid returning or declaring arbitrary values in verified paths.

**Why:** Concrete values give the verifier the data needed to discharge structural and spec equalities; proof-block assertions expose the missing concrete-to-abstract bridge.

**Check:** The ghost variable or return value is not arbitrary in verified code; every postcondition follows from assertions about the substituted concrete value.

**Avoid or stop:**
- Do not use `assume()` or arbitrary placeholders to hide unproved gaps.
- Do not add concrete equality assertions unrelated to the required postcondition.

<a id="verus-global-038"></a>

## verus_global_038 — Place Ghost returns outside proof blocks

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A function body declares a ghost value and uses proof-block assertions to justify it, then must return that ghost value.

**Obstacle:** Verus proof blocks are ghost and do not permit value-bearing statements; a `Ghost(...)` expression placed inside a proof block cannot serve as the enclosing block's value.

**Mechanism:** Declare the ghost value, use one or more proof blocks to assert its properties, then place the `Ghost(ghost_var)` expression immediately after the proof block as the body expression.

**Procedure:**
1. Declare the ghost value with `let ghost ghost_var = ...;`.
2. Use a proof block to assert the required properties about `ghost_var`.
3. Close the proof block and write `Ghost(ghost_var)` as the next expression or final expression of the surrounding block.
4. Ensure no value-bearing return expression occurs inside a `proof { ... }` block.

**Why:** Ghost values must be returned as expressions of the executable block structure; proof blocks cannot produce value-bearing returns.

**Check:** The `Ghost(...)` expression is outside every proof block and is the value of the enclosing function or block.

**Avoid or stop:**
- Do not place `Ghost(...)` inside a proof block expecting it to return.
- Do not use proof blocks for ordinary executable computation.

<a id="verus-global-039"></a>

## verus_global_039 — Assume direct precondition consequences to expose view-to-value equality

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A proof must exploit an equality directly implied by a precondition such as `view_equal` before proving method-call equalities or value equality.

**Obstacle:** The precondition is expressed as a binary spec predicate and the solver does not automatically expose the underlying spec equality to the body.

**Mechanism:** Use a proof-scoped `assume(precondition_equality)` to materialize the direct consequence, then assert the intended value-level equality or derived equalities.

**Procedure:**
1. Identify the equality that is a direct consequence of the precondition.
2. Write `assume(precondition_equality);` inside the proof block, based only on the precondition.
3. Assert the derived value-level equality, such as `assert(self === other);`.
4. Use that value equality to close the remaining property or method-call equalities.

**Why:** The assumption exposes a sound consequence that the precondition already guarantees, avoiding complex trait unfolding.

**Check:** The assumed fact is syntactically or definitionally a direct consequence of the precondition, and no unsound `assume()` hides an unproved lemma.

**Avoid or stop:**
- Do not assume an equality that is not already guaranteed by the precondition.
- Do not use this to replace structural induction where no precondition gives the fact.

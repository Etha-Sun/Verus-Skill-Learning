# Temporal and Execution Proof Patterns

Use when the failing obligation involves temporal/execution predicates, `spec.entails`, `leads_to`, `tla_exists`, temporal predicate equality, nested temporal operators, suffix rewriting, or spec-level higher-order temporal proofs.

## Reproduce and confirm the obligation

Run Verus on the target file before editing (do not rely only on pre-existing logs), and confirm the unproved obligation is the stated temporal goal.

## Quantified temporal preconditions

Place `#[trigger]` on the outer `spec.entails(...)` inside the `forall`, not on the `leads_to` subexpression.

```rust
// Works
forall |msg| #[trigger] spec.entails(P(msg).leads_to(Q))

// Rejected
spec.entails(#[trigger] P(msg).leads_to(Q))
```

## Concrete state to TLA existential

When a named predicate is semantically existential but not syntactically `tla_exists`, prove the entailment explicitly by extracting the witness from the state.

1. Define the indexed predicate, e.g. `b_to_middle(req_msg)`.
2. Prove `concrete.entails(tla_exists(b_to_middle))` with an execution-level assertion over `satisfied_by(ex)`.
3. Inside that assertion, read the witness directly from the state.
4. Assert the indexed predicate on that witness and conclude the TLA existential.

This makes `leads_to_exists_intro` results usable with `leads_to_trans` and `entails_implies_leads_to`.

## Named existential start predicates

Do not rely on Verus to unfold a named existential precondition into its `tla_exists` form. Prove both entailment directions manually:

1. Define the start state from the named predicate.
2. Show `start.entails(tla_exists(P))` by choosing a definitional witness.
3. Show `tla_exists(P).entails(start)` by reading the witness's component properties back into the named predicate.
4. Use `entails_implies_leads_to` to lift the implication and `leads_to_trans` to chain the start state to the final goal.

## Temporal / execution predicate equality

- Apply `temp_pred_equality` to reduce equality of temporal predicates into two entailment obligations: `lhs.entails(rhs)` and `rhs.entails(lhs)`, then prove each separately.
- For temporal predicate equality such as `always(always(p)) == always(p)`, apply the supplied equality axiom and split into two entailment directions: one by instantiating the outer temporal operator at an appropriate suffix, and the other by showing the property holds at every suffix.
- For an existential predicate under `tla_exists`, use `choose` to obtain a witness from the existential and assert that the chosen witness predicate is `satisfied_by` the same execution.
- Introduce a `let` binding that exactly matches the predicate in the goal before asserting, for example `let a_to_p_and_q = |a: A| a_to_p(a).and(q);`, and use that bound name in both the `exists` assertion and the witness-satisfaction assertion.
- Run Verus immediately after drafting the proof. Treat the first failed assertion as a trigger-alignment issue; make the minimal syntactic alignment edit before changing the proof strategy.

## Nested temporal operators

When the unproved obligation is a nested temporal formula such as `always(always(p))`:

1. Run Verus on the original file and read the generated log to confirm the exact unproved obligation is the nested temporal formula.
2. Rewrite the outer operator with its definition. For `always(always(p))`, expand the outer `always` so the goal is pointwise over suffixes: `forall |i: nat| always(p).satisfied_by(ex.suffix(i))`.
3. Prove the pointwise goal with an `assert forall` block; inside each quantified case, invoke the existing suffix-transfer lemma rather than re-proving temporal propagation by hand.
4. Verify the lemma name and argument order against the local vstd or guide declaration before using the snippet.

## Temporal suffix proofs

Use when a Verus proof requires rewriting nested execution suffixes, propagating `always` facts before a forall over future states, or closing a one-step temporal shift with stability induction.

### Suffix composition

Add a small composition lemma proven by pointwise state equality:

- Define `proof fn suffix_composition<T>(ex, i, j)` ensuring `ex.suffix(i).suffix(j) == ex.suffix(i + j)`.
- Prove it by asserting `nat_to_state` equality for every index `k`, then call `execution_equality`.
- In the main proof, use this lemma after deriving `later(q)` to close the one-step shift from `suffix(idx).suffix(1)` to `suffix(idx + 1)`.

### Propagate `always` facts before proving a forall over future states

Before asserting `forall |k| q.satisfied_by(ex.suffix(i).suffix(witness_j).suffix(k))`, call `always_propagate_forwards` for both `next` and the stability formula `q.and(next).implies(later(q))`. Then assert those `always` facts at `ex.suffix(i).suffix(witness_j)`.

### Close the one-step shift with stability induction

Inside a forall over future indices:

- Assume `q` and `next` at `suffix(idx)`.
- Assert `q.and(next)` and call `implies_apply` to obtain `later(q)`.
- Rewrite `later(q)` as `q` at `suffix(idx + 1)` using the suffix-composition lemma.
- Call `next_preserves_inv_rec` on the suffix execution to lift stepwise preservation to an arbitrary future index `k`.

## Recursive induction over execution positions

For recursive temporal assertions over a position index, prove the result by direct induction on the index.

- Branch on `i == 0`.
- In the inductive branch, recursively call the same lemma on `(i - 1) as nat`.
- Assert the predecessor-version preconditions.
- Derive the current-position conclusion from the recursive result, the step preconditions, and the fact that `!q` forces `p` at `i`.

## Arithmetic indices for `execution.suffix`

When passing arithmetic expressions to `execution.suffix`, cast them explicitly to `nat`.

For example, use `(i - 1) as nat` and `((i - 1) + 1) as nat` in suffix-position assertions. Without these casts, Verus may reject the expression as type-incorrect or fail to connect adjacent positions.

## Conjunction entailment with library combinators

Reuse existing combinators before manual quantifier or unfolding reasoning.

- To prove `p.entails(p.and(q))`, apply `entails_and_temp`.
- For the missing reverse direction, add or reuse a focused lemma such as `p_and_q_entails_p` that proves `p.and(q).entails(p)` once, then call it in the main proof.

## Entailment to a local fact with `implies_apply`

When a proof has `spec.entails(q)` and the current execution satisfies `spec`:

1. Assert `spec.implies(q).satisfied_by(ex)`.
2. Call `implies_apply(ex, spec, q)` to derive `q.satisfied_by(ex)`.

Also use `entails_apply` when the proof already has `spec.satisfied_by(ex)` and an entailment, or `entails_implies_leads_to` for lifting implications to leads-to.

## Reducing `always(p)` at suffix index 0

When `always(p).satisfied_by(ex)` is available and the goal is a current-state property:

1. Instantiate `forall |i: nat| p.satisfied_by(ex.suffix(i))` at `i = 0`.
2. Use `execution_equality` to show `ex.suffix(0) == ex` by proving equality of their `nat_to_state` functions.
3. Conclude `p.satisfied_by(ex)`.

## Execution suffix equality via `execution_equality`

When reasoning about suffix composition such as `ex.suffix(i).suffix(j)`, assert pointwise equality of their `nat_to_state` projections, then call `execution_equality` on the related suffix expressions.

## Unfold `always` before pointwise reasoning

- Start by deriving pointwise suffix facts with `always_unfold(ex, P)`.
- This exposes `P.satisfied_by(ex.suffix(i))` for every index `i`, matching the shape of pointwise postconditions.

## Discharge universal pointwise targets with an explicit assert-forall

After unrolling, state the exact universal target over suffix state:

```rust
assert forall |i| p(ex.suffix(i).head(), ex.suffix(i).head_next());
```

Adjust the predicate and accessors to the current obligation. Keep the assertion proof-only; do not alter the function contract or executable code.

## Triggering quantified assertions

If a quantified equality/assertion over execution state positions or `nat` indices is not automatically instantiated, annotate the quantified formula with `#[trigger]`:

```rust
assert forall |x: nat| #[trigger] ex.suffix(i).suffix(j).nat_to_state(x)
    == ex.suffix(i + j).nat_to_state(x) by { ... };
```

## Trigger-note cleanup with `#![auto]`

When a quantified assertion verifies but emits trigger warnings, annotate the quantifier with `#![auto]` immediately after the binder:

```rust
assert forall |ex: Execution<T>| #![auto] ...;
```

This suppresses trigger warnings and keeps the proof accepted without changing surrounding proof structure. Re-run Verus for a clean final run.

## Transitivity / simple leads-to chain

When proving `p.leads_to(q)` or a leads-to transitivity goal:

1. Unfold `p.leads_to(q)` as `always(p.implies(eventually(q)))`.
2. Assert the quantified implication over executions satisfying `spec`, e.g.:
   `assert forall |ex| #![auto] spec.satisfied_by(ex) implies ...;`
3. Chain the two premises using the supplied temporal lemmas:
   `always_unfold`, `eventually_unfold`, `implies_apply`,
   `entails_apply`, and `eventually_propagate_backwards`.
4. Re-run Verus. If verification succeeds but reports only automatic trigger notes, keep the proof and add the suggested `#![auto]` annotation to the quantified assertion, then re-verify for a clean run.

## Decompose compound leads-to goals

When a direct implication from the original initial state predicate to the final temporal predicate does not verify:

1. Define a `lift_state` predicate for each intermediate proof stage.
2. Prove each stage separately with the corresponding helper lemma:
   `spec.entails(param_pred(msg).leads_to(mid_state))`
3. Lift each stage to `tla_exists` with `leads_to_exists_intro`.
4. Combine the lifted stages with `leads_to_trans`.

Do not try to prove the whole chain as a single direct implication from the initial state to the final state.

## Prove state-to-existence implications over `Execution<State>`

When a state predicate implies an existential temporal predicate:

1. Quantify over `ex: Execution<State>`, not bare `State`.
2. Let `s = ex.head()`.
3. Extract a witness with `choose` from an in-flight or pending message field.
4. Assert the chosen witness satisfies the desired predicate on `ex`.
5. Call `entails_implies_leads_to` to finish the implication.

Replace `State` with the current system state type, for example `ClusterState`. Treating a bare state as an execution does not match Verus's temporal satisfiability relation.

## Spec-level higher-order proof patterns

Use these patterns when the Verus obligation is a spec-level higher-order temporal proof: a `forall` over `always`/`entails`, a pointwise entailment side condition, or a lambda term that must be used in triggers or axiom arguments.

### Bind inline lambdas to local names

Bind each inline spec lambda to a local `let` name before using it in triggers, assertions, or lemma/axiom calls. Reuse the same named binding everywhere the term occurs.

### Prove pointwise entailment side conditions with `assert forall`

For a higher-order lemma precondition that requires pointwise entailment, assert both directions together with an explicit trigger:

```rust
assert forall |a| #![trigger f(a)]
    f(a).entails(g(a)) && g(a).entails(f(a));
```

Close each direction with `=~=` equalities to a common predicate. The explicit trigger controls quantifier instantiation; `=~=` lets Verus prove extensional equivalence by simplification rather than manual expansion.

### Keep reasoning at the spec level

Prefer `a.entails(b)` with `=~=` over expanding to `implies(a.satisfied_by(arbitrary()), b.satisfied_by(arbitrary()))`. Do not expand spec-predicate implications over traces unless the observable diagnostic requires it.

## Proof annotations only / Validate the repair

In verification benchmark tasks, add only proof annotations inside the function body. Keep original function signatures and executable code unchanged. Rerun Verus after adding only these proof annotations, and require a clean final run; run it twice to confirm the result is stable before declaring success.

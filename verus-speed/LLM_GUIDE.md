# Writing Verus proofs that verify fast: guidance for an LLM prover

Evidence tags: **[measured]** = measured in this repository on VeruSAGE tasks
(see `README.md` and the proof-time study in `research_memory`);
**[community]** = standard Verus practice from the Verus guide, not measured
here. Follow the measured items first.

## 0. Decide whether speed matters for this file

- Run `verus FILE --time-expanded --output-json` and read `smt.smt-run`.
- **[measured]** If solver time is under about 1 s, stop. About two thirds of
  benchmark files spend under 0.2 s in the solver; their run time is fixed
  start-up cost that no proof edit changes, and removable proof cost is about
  4%. Spend effort only on files where solver time exceeds 1-2 s.
- **[measured]** Do not use the `rlimit-count` field of Verus 0.2025.09.12 to
  compare functions: it is attributed to the wrong query. Use per-function
  `time-micros`, or `scripts/proof_time/smt_replay.py` for exact cost.

## 1. Rules while writing (cheap to follow, no measurement needed)

1. **[measured]** Do not assert a large predicate you do not use. Every
   `assert(P)` is a proof obligation. When `P` is a `wf()`/invariant predicate,
   a transition relation (`next_step(...)`), a refinement relation, or equality
   of whole structs, sequences or maps, the solver must unfold `P` and
   case-split just to prove it. This is the largest avoidable cost found: in
   13 of 68 heavy human proofs, deleting one such statement cut cost by more
   than 30% (example: 30 s -> 11 s from one deleted `assert forall`).
2. **[measured]** Do not write `assert forall ... by { }` that restates a fact
   nothing later uses.
3. **[measured]** Keep statements that do real work: one that establishes the
   precondition of the next lemma call, introduces a witness, instantiates a
   quantifier at a specific term, or is a loop invariant. Deleting these does
   not make the proof cheaper; on heavy proofs it often makes the solver run
   more than 4x longer before failing.
4. **[measured]** Small facts (one equality, simple arithmetic, one membership)
   are cheap either way. Do not spend effort removing them.
5. **[measured, weak: 2 of 2 tasks]** Put invariant-preservation reasoning in a
   helper lemma with a narrow `requires`/`ensures` instead of inline in a large
   function. The helper is verified in a small context, and the caller only
   sees its `ensures`.
6. **[measured]** Prove the specific instance or witness the goal needs, not
   the general statement.

## 2. Structural tools for a function that is still slow

7. **[measured]** `#[verifier::spinoff_prover]` on one heavy function gives it
   a fresh solver context. It helped strongly on a few heavy functions (best
   0.25x) and made others worse, and it always adds start-up cost. Apply it to
   one function, measure, and keep it only if it wins. Never apply it to small
   functions.
8. **[community]** Scope hints with `assert(P) by { ... }`: facts and lemma
   calls inside the block are not visible after it, so they cannot trigger
   further instantiations in the rest of the function.
9. **[community]** Mark a large spec function `#[verifier::opaque]` (or
   `closed`) and `reveal(f)` only inside the `assert ... by` block that needs
   its body. Spec-function unfolding was the largest source of quantifier
   instantiations in heavy proofs here (median 42%) **[measured]**.
10. **[community]** Isolate arithmetic: `assert(...) by (nonlinear_arith)
    requires ...;` and `by (bit_vector)`, each with only the facts it needs.
    Never leave nonlinear goals to the default solver context.
11. **[community]** Give every hand-written quantifier an explicit
    `#[trigger]` on the most specific term; avoid triggers that match their
    own instantiation (matching loops).
12. **[community]** `broadcast use` only the specific lemma or small group you
    need, inside the function or block that needs it. **[measured]** Unused
    `broadcast use` lines cost 0-3% here, so this is hygiene, not a main lever.
13. **[community]** Keep loop invariants to what the loop body and the
    postcondition need; a restated global invariant is re-proved on every
    iteration path.

## 3. After the file verifies: measure, then clean

**[measured]** This procedure is the only agent-side intervention that reduced
final proof cost on heavy tasks (0.87x at 1.24x agent time); text rules alone
did not (about 1.0x).

1. Find the most expensive function you wrote (per-function `time-micros`).
2. In it, list asserts of large predicates that the next step does not use.
3. Delete or narrow one or two per round, re-verify, keep the change only if
   the file still verifies and the function got cheaper.
4. Stop when no candidate remains, or solver time is under 1 s.

`verus-speed/auto_speed.py` performs this search mechanically (no LLM) and
reached 0.78x on 67 heavy human proofs.

## 4. What does not help (so do not spend tokens on it)

- **[measured]** Removing duplicated small asserts or tidying `assert by`
  scoping on light files: 0-3%.
- **[measured]** Re-running with other solver seeds and taking the fastest:
  about 9% on heavy files for 3x the CPU.

## 5. How to call Verus while iterating

- **[measured]** While the proof still fails, call Verus with
  `--multiple-errors 0 --no-auto-recommends-check`. Failing runs take 0.86x
  the time; the verdict is unchanged. You get one error per function and no
  `recommends` notes, so drop the flags when one error message is not enough
  to locate the problem.
- Run the plain command (no extra flags) for the final check.
- **[measured]** Do not use `-V spinoff-all` or more threads on a single-file
  task: one function carries nearly all solver time (median 99.5%), so there
  is nothing to parallelize.

## 6. Working inside a whole repository

- **[measured]** While iterating on one proof in a large crate, verify only
  that function: `--verify-only-module MODULE --verify-function NAME`. In
  NRKernel this takes 7.4 s instead of 79 s, in the Anvil controller 16 s
  instead of 175 s. Run the full check once at the end. On a small crate
  (IronKV, 8 s in full) just run the full check.
- **[measured]** If you add a helper lemma, put it in the same module and
  verify it the same way; if you change a `spec` function or any
  `requires`/`ensures`, callers are affected and only a full check counts.
- **[measured]** A full check waits for the slowest function, not for the
  number of functions. A proof you make heavy (tens of seconds of solver
  time) slows every later full check of the repository, so the rules in
  sections 1-3 matter more here than on single files.

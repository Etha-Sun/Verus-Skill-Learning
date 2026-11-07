# Verus proof time measurement and proof speed learning study

## Metadata

- project: `verus_self_evolving`
- kind: `experiments`
- created_at: `2026-11-06T16:00:45`
- status: `complete`
- motivating meeting: `../../meetings/20261106-150340-proof-time-as-evaluation-metric-and-skill-learning-reward-meeting/ENTRY.md`
- code: `scripts/proof_time/` (commits `1205049`, `1b28cf5`)
- outputs: `$VERUS_SKILL_RUN_ROOT/proof-time-study-20261106/` (local machine:
  `~/verus-skill-runs/proof-time-study-20261106`), not committed
- toolchain: Verus 0.2025.09.12.bb1f342 + bundled Z3 4.12.5; human proofs from
  VeruSAGE-Bench ground truth (`microsoft/verus-proof-synthesis`, cloned shallow)

## Objective

Before running large DeepSeek skill-learning experiments, establish
(1) a trustworthy proof-cost metric, (2) which proof-writing behaviours causally
change solver cost, (3) whether deliberately optimized proofs are measurably
faster, (4) how long failing proofs take to verify.

## Measurement method (most solid result)

- **Verus's built-in per-function `rlimit-count` is wrong in this version.**
  Z3 statistics are refreshed only *before* each query, so each function is
  charged the previous query's cost, and the last query of each context
  (including every spinoff function) is never counted.
  Evidence: 11 distinct Unpack proofs all reported exactly 2670; the 142 s AC
  query reported 60,891 versus its true 99,031,273.
- **Exact replacement:** `smt_replay.py`.
  - Run Verus with `--log smt`.
  - Drop Verus's own `(get-info ...)` lines.
  - Add `(get-info :all-statistics)` after every `check-sat`.
  - Replay the log in the same Z3.
  - Attribute rlimit and quantifier instantiations (QI) to each `;; Function-Def`.
  - A first version mis-paired statistics blocks; it was fixed and all affected
    outputs were rerun.
- **Stability:** exact rlimit across 2 seeds has a median max/min of 1.000
  (p90 1.004). Wall time varies about 5% and SMT time about 7% (p90 18%)
  across 10 seeds.
- **Validity as a time proxy:** across 68 heavy tasks, log-log correlation of
  rlimit with Z3 time is 0.86. Within confirmed variants, it is 0.62.
- **Superseded / retracted:** the lagged-metric results ("LLM proofs 1.83x
  human", "30x within-task spread") are wrong. They are archived under
  `superseded_*` in the run directory.

## Experiments and results

1. **Benchmark-wide proof time** (802/849 human proofs measured, 3 runs each).
   - Median wall time is 0.64 s, and SMT is a median 5% of wall time.
   - 12% of tasks spend more than 1 s in SMT, and 3% take more than 10 s.
   - Heavy tasks concentrate in AC (up to 142 s), OS (52 s) and NR (36 s).
   - The AL/IR/NO/VE/ST tasks are solver-light.
   - 47 proofs did not verify in this environment.
2. **Human vs DeepSeek** (50 fixture tasks, target function plus
   LLM-added helpers, exact rlimit).
   - Geometric mean LLM/human is 1.03; the best LLM proof is 0.94.
   - The LLM proof is more than 10% slower on 30% of tasks and more than 10%
     faster on 22%.
   - No systematic "LLM proofs are slower" effect on these tasks.
3. **Within-task correlation** (358 DeepSeek proofs, 52 tasks).
   - QI vs rlimit: rank correlation 0.87. Proof lines: 0.56. Asserts: 0.32.
   - Spread between proofs is small: median max/min is 1.125, and only 6% of
     tasks exceed 2x.
4. **"Add a bad habit" perturbations** (130 small proofs).
   - Duplicating asserts: +0–2%.
   - Module-level `broadcast use` of 4 large vstd groups: +0.3–1.5%.
   - Dropping explicit triggers breaks about half of the proofs, and adds
     +0.3–3% when the proof still verifies.
   - Unscoping `assert by`: about 0%.
5. **Attribution of existing optimizations** (151 single edits from 44
   improving pairs).
   - Optimizer pairs: median saving 1.4%, and the single best edit explains
     about 99% of each pair's saving.
   - Only 3/83 DeepSeek edits saved more than 5%. `let` bindings saved nothing
     and broke 6/10 attempts.
   - Effective small-task edits:
     - deleting an unneeded `assert(eventually(q).satisfied_by(..))`: -38%;
     - replacing `assert_seqs_equal!` with `lemma_concat_associative`: -31%;
     - deleting unneeded `assert forall` blocks: -5 to -8%.
6. **Heavy-task QI profile** (68 human proofs with SMT > 2 s).
   - QI comes mainly from spec-fn definition unfolding (median share 42%) and
     Verus prelude axioms (14%): integer bounds `u_inv`/`u_clip` and Option
     boxing. User-written quantifiers account for 7%.
   - No matching loops: the top-1 quantifier share has median 12%, and none
     exceeds 30%.
   - In a 30 s NR task, the Verus profiler saw only 64 user-level
     instantiations.
7. **Heavy-task single-factor ablation** (1,392 variants, one change each,
   exact rlimit, timeout 4x baseline).
   - In 33/68 tasks some single change cuts cost by more than 10%; in 13/68 by
     more than 30%. The median per-task best is 0.895.
   - Most single deletions do nothing: median ratio 1.000.
   - `del_assert`: 748/868 still verify, 85 save more than 10%, 109 cost more
     than 10%.
   - `add_spinoff_prover`: 8 tasks save more than 10% (best 0.25), 4 cost more
     than 10%.
   - Deleting `assert by` / `assert forall` / `broadcast use` / `reveal` mostly
     breaks the proof.
   - Mechanism, confirmed by QI profiles of the top 10 deletions: asserting an
     unneeded large predicate (`wf()`, `next_step(..)`, struct-field equality,
     big `forall`) creates a proof obligation. Discharging it unfolds
     definitions and case-splits. Definition QI, prelude QI, decisions and
     added-eqs all drop by 30–60% when it is removed.
8. **Real-seconds confirmation** (49 variants with rlimit ratio < 0.8, 3 seeds).
   - 48/49 verify on all seeds.
   - Median SMT-time ratio is 0.72, and 36/49 are below 0.8x.
   - Examples: 30.2 s -> 10.8 s and 32.9 s -> 14.8 s (NR, deleting one
     `assert forall|s| pred(s,s) by {}`); 9.7 s -> 3.8 s (AC, spinoff).
9. **Failing proofs** (607 archived DeepSeek episodes, about 3,800 verifier
   calls).
   - Failing calls are about 25% faster than passing calls on the same task
     (median ratio 0.75).
   - Errors before SMT take a median 0.19 s.
   - No rlimit-exceeded failures occurred.
   - Verifier time is a median 1% of episode wall time (p90 3.6%).
   - On heavy proofs, removing a needed statement often makes the run exceed
     4x baseline instead of failing fast: 18/23 `reveal` deletions and 25/208
     `assert by` deletions, 71/1,324 variants in total.
10. **DeepSeek optimizer** (train 33 tasks, 4 rounds, no cards).
    - Geometric-mean rlimit ratio 0.956; 7 tasks save more than 5%; best 0.605.
    - Many rounds failed (verify_fail, apply_error).
    - Assert-pruning baseline without an LLM (val 17): 0.941, 6 tasks save more
      than 5%.

## Follow-up 2026-11-06 (later): search post-processing and "can guidance spot costly statements"

User direction: relative gains on small tasks also count; hope heavy-task lessons transfer.

11. **Search post-processor** (`speed_search.py`, no LLM): verify every single
    change in the proof region, apply beneficial ones greedily, and confirm the
    result on seeds 1 and 2.
    - Heavy human proofs (67 tasks): geometric-mean ratio 0.781, median 0.900.
      - 46 tasks save more than 5%, 23 more than 20%, 7 more than 50%.
      - All results verify on the other seeds.
      - Changes applied: 92 assert deletions, 14 assert-by deletions,
        5 assert-forall deletions, 13 spinoff additions, 3 broadcast deletions.
      - Most useful statement shape: an assert of a predicate call (108
        deletions save more than 5%, 28 more than 20%).
    - Small DeepSeek proofs (50 tasks): geometric-mean ratio 0.958, median 0.991.
      - Only 12 tasks save more than 5%, and 2 more than 20%.
      - About 90% of their asserts can be deleted individually, at roughly 0%
        each.
      - spinoff hurts small proofs (median ratio 1.18).
      - Comparable to the DeepSeek optimizer (train 0.961 vs 0.956) and to
        assert pruning (val 0.952 vs 0.941).
    - Transfer: the mechanism is the same on small and heavy tasks (unneeded
      obligations unfold definitions). Small proofs simply have little such cost.
12. **Ranking evaluation** (`rank_eval.py`). Labels are the heavy single-deletion
    results: a positive keeps the proof verified and cuts rlimit by 10% or more.
    - Data: 63 tasks split train 33 / test 30 by project; 16 test tasks have
      positives; random precision@5 is about 8% overall.
    - DeepSeek V4 Pro (effort high) picks the top 5 of the marked statements in
      the target function, 3 repeats per condition.
    - A first run used max_tokens=16000; the reasoning consumed the budget,
      giving empty answers. It was discarded and rerun with 64000.
    - Test, tasks with positives only:

      | Condition | Precision@5 | Saving captured |
      |---|---|---|
      | none | 0.258 | 0.679 |
      | rules | 0.242 | 0.673 |
      | cards (learned from train single-factor contrasts) | 0.217 | 0.652 |
      | heuristic | 0.213 | 0.655 |
      | random | 0.196 | 0.667 |

    - Paired comparisons on test are all near even: cards vs none 4/5/7
      (wins/losses/ties), rules vs none 3/4/9.
    - On train (in-sample), cards beat none 9/3. The cards fit the train
      proofs but did not transfer to held-out tasks.
    - "Saving captured" is a weak metric: random already reaches 0.67 because
      positive tasks often hold several costly deletable statements.
    - Cost: about 17M input tokens (cached) and 16M output tokens. The account
      balance fell by about $60 over this period; the key may be shared.

## End-to-end A/B (2026-11-07): does speed guidance change the proofs DeepSeek writes?

- **Learning data.** No new sampling: the 40 train tasks already had 169
  verified DeepSeek proofs. The search post-processor labeled every statement
  in them (168 proofs; geometric-mean removable cost 0.965; 45 statements save
  more than 5%).
  - DeepSeek distilled 5 "small-task" cards from the labels (1 costly to 3
    others).
  - Skill B (rules) = evidence rules + these cards.
  - Skill C (procedure) = post-verification cost procedure plus a
    `tools/proof_cost.sh` exact-cost tool. Files are in
    `scripts/proof_time/skills/`.
- **Harness** (`scripts/proof_time/e2e_codex.py`): the real Codex agent
  (codex-cli 0.164, original contract 0.147) drives DeepSeek V4 Pro (effort
  max) through DeepSeek's native Responses API.
  - The prompt, workspace layout and 600 s budget are the same as the earlier
    project contract.
  - Substitutions: Codex's workspace-write sandbox instead of the outer
    namespace sandbox, and proof_guard instead of Lynette.
  - A lightweight self-written loop was piloted first and abandoned: it solved
    1/4 of episodes versus 82% historically for the Codex harness.
- **Design.** Val 20 tasks x 3 conditions x 4 repeats = 240 episodes. Exact
  final cost uses SMT replay of the target fn plus helpers the proof added.
  Paired comparisons use per-task medians over solved repeats, with a
  sign-flip permutation test.
- **Solve rates.** base 51/80, rules 57/80, procedure 49/80.
  - Every failure was a timeout.
  - "Verified at some point but broken at the deadline": base 11, rules 5,
    procedure 11.
- **Final proof cost vs base** (14 paired tasks):
  - rules: 0.972, p=0.029; 2 tasks more than 5% cheaper, 0 more costly.
  - procedure: 0.952, p=0.18; 2 cheaper, 1 costlier.
  - procedure vs rules: 0.982, not significant.
  - Noise floor: the same task and condition across repeats varies with a
    median max/min of 1.04.
  - For scale, the search upper bound on val small proofs was 0.952.
- **Agent time.** procedure takes 1.40x base actor wall time (p=0.009) and 8 vs
  5 Verus calls per episode. rules: 0.98x, not significant.
- **Verification of the procedure.** All 23 solved procedure episodes checked
  mid-run ran the cost tool, and 20 edited the proof after seeing costs.
- **Cost.** Balance 2580.46 -> 2541.83 ($38.6, about $0.16/episode, off-peak
  weekend pricing). Pilot and smoke runs cost about $1.4 more.
- **Interpretation.**
  - Writing guidance distilled from measured single-statement contrasts gives
    a small but consistent reduction in what DeepSeek writes (about 3%; no task
    became costlier) at no time cost.
  - The measure-and-clean procedure reaches the search upper bound (about 5%)
    but costs 40% more agent time.
  - On these small tasks the absolute effect is tiny (milliseconds of SMT).
    Heavy tasks (AC/OS/NR) are where it would matter, and no end-to-end run
    there exists yet.
  - This contrasts with the ranking eval: guidance did not help *identify*
    costly statements in an existing proof, but did slightly change *writing*.

## Heavy-task end-to-end A/B: setup and expectations written before running (2026-11-07)

- Tasks: VeruSAGE-Bench AC/OS/NR heavy tasks (human proof Z3 time 2-35 s)
  outside the 80-task fixture, so none is in the train split the cards came
  from. Kept only tasks whose human proof passes the proof-only guard (40).
- Guard fixes made first. Both were found because human proofs failed the
  guard. Neither affected any val episode.
  - Adding or removing `#[verifier::spinoff_prover]` is proof-only.
  - `broadcast use` statements inside exec bodies are proof-only.
- Caveat: the generic RULES text was written partly from heavy-task ablations
  on human proofs of some of these same tasks. The rules are not
  task-specific, but this is a mild leak in favour of `rules`.
- Budget is raised to 1200 s, because one Verus call takes 3-30 s here.
- Isolation fix (found in pilot transcripts). Codex's workspace-write sandbox
  does not restrict reads, so agents could `find`/`rg` the home directory.
  - The benchmark clone with human proofs was reachable.
  - Codex also listed the user's `~/.codex/skills`.
  - Audit of the 240 val episodes:
    - none opened a verified copy of its own target;
    - 3 saw benchmark paths or snippets in search output;
    - one of those saw two lines from a sibling task's verified file.
    - These are spread across conditions, so the val conclusions stand, with
      this caveat.
  - Heavy runs use `e2e_codex.py --sandbox` (bwrap):
    - all home dirs (the parent of `$HOME`), the shared data mount (`--hide`) and `/tmp` are hidden;
    - toolchains, node/codex and the guard/cost scripts are exposed read-only;
    - only the episode dir is writable;
    - Codex gets a fresh empty `CODEX_HOME`;
    - stdin is `/dev/null` (Codex otherwise waits on stdin under bwrap).
- Pilot, unsandboxed, so not merged into the main run; base, 1200 s:
  - 1/3 solved: the OS task in 329 s.
  - The AC and NR agents spent all 1200 s reading the 4-5k-line file and
    never edited it.
  - Cost $0.90, about $0.30/episode.
- Main step 1: the 16 tasks in `e2e_heavy_main.jsonl`, fixed before any pilot
  result was seen, × 3 conditions × 1 repeat. Add a second repeat only if at
  least 8 tasks are solved in two or more conditions.
- Expectations, written before seeing any data:
  - Solve rate will be well below val. Many tasks will have zero solves in
    every condition, so paired power is low; at least ~8 tasks need solves in
    two or more conditions.
  - On human proofs of these tasks, search removed about 22% (geomean 0.78).
    If DeepSeek's proofs carry similar redundancy:
    - `procedure` could reach about 0.8-0.9x cost;
    - `rules` about 0.9-0.97x.
  - The `procedure` time overhead will be larger than on val, because each
    cost-tool call replays a 3-30 s query.
  - A null result is plausible if DeepSeek writes minimal proofs on heavy
    tasks, which is likely under time pressure.

## Heavy-task end-to-end A/B: results (2026-11-07)

- Run: sandboxed, 1200 s budget.
  - Repeat 1: 16 tasks × 3 conditions.
  - Repeat 2: the 9 tasks solved at least once × 3 conditions.
  - 75 episodes in total.
- Cost: $17.96 for pilot + smoke + main (balance 2541.79 -> 2523.83), about
  $0.24/episode, off-peak.
- Solve rate: base 16/25, rules 15/25, procedure 15/25.
  - 6 tasks were never solved: all 4 AC tasks, 1 NR, 1 OS.
  - Failures were mostly reading the 4-5k-line file until the budget ran out.
- Target-function cost, paired over the 9 tasks solved in both conditions
  (per-task median over solved repeats):
  - procedure / base: 0.868 (5 cheaper by >5%, 2 costlier; p=0.16).
    Actor time 1.24x (p=0.046).
  - rules / base: 1.036 (p=0.87); no effect.
  - Noise: same task and condition across repeats, max/min median 1.06 but
    p75 1.53. Different solution paths differ hugely, e.g. new_endpoint
    ranges from 25M to 105M rlimit within one condition.
- Against the expectations written beforehand:
  - procedure 0.8-0.9 was expected; 0.87 was observed, but it is not
    significant with 9 tasks.
  - rules 0.9-0.97 was expected; no effect was observed.
  - On val, rules gave 0.97 and was significant; that small edge does not
    show on heavy tasks.
- Mechanism example: run_blocked_thread, repeat 1.
  - base: a 99-line manual proof with 51 asserts, 23.1M rlimit.
  - procedure: its first verified proof was 8.4M (a different path). About
    30 cost-guided deletions of asserted large predicates (`threads_cpu_wf`,
    `cpus_wf`, ...) brought it to 4.6M.
  - rules: 7.0M and 7.3M in both repeats.
  - This is the "unneeded assert of a large predicate" mechanism from the
    heavy ablations, now found by the agent itself.
- Takeaways:
  - On heavy tasks, variation between solution paths for the same task is
    larger than the effect of any skill text tried.
  - Measured cost feedback (procedure) is the only lever that showed a
    consistent direction.
  - Same-task, different-path contrasts (e.g. 23M vs 4.6M, both verified,
    same agent) are natural, strong learning signal for cost-aware cards or
    for best-of-k selection.

## Same-task cost-contrast pairs (2026-11-07, `mine_pairs.py`)

- Pool: 561 verified DeepSeek proofs over 60 tasks, from historical runs, val
  e2e and heavy e2e, each with an exact target-function cost.
- Small tasks have almost no contrast:
  - train: 6 of 34 tasks have a pair at 1.5x or more, the largest 2.2x;
  - selection (val): 3 of 17.
  - Absolute costs are tiny (0.03-0.4M rlimit).
- Large contrasts appear only on heavy tasks: shootdown 9.7x,
  run_blocked_thread 5.4x, new_endpoint 4.1x, plus 2 tasks around 1.6-1.7x.
- Cost is not monotone in the number of asserts.
  - new_endpoint: the cheapest proof (25M) asserts each `wf` conjunct
    separately (19 asserts) before the closing lemma call. The costliest
    (104M) asserts `self.wf()` as one obligation.
  - run_blocked_thread and block_running_thread: re-asserting `wf`
    conjuncts that were not needed made the proof costlier (15.7M vs 9.2M).
  - So the useful lesson is conditional:
    - split a large obligation that must be proved into its conjuncts;
    - do not assert large facts that are not needed.
  - Surface rules such as "fewer asserts" cannot express this, which fits the
    null rules result on heavy tasks.
- Consequence: pair-based card learning needs more same-task samples on heavy
  tasks; the existing train split has too little contrast.

## Pair-card learning: design and expectations, written before running (2026-11-07)

- Training pool: the 9 heavy tasks solved before. 4 more base samples each
  (repeats r2-r5, same sandboxed harness, 1200 s), added to the existing
  proofs.
- Cards: DeepSeek sees, per training task, the cheapest and costliest verified
  proofs. The prompt carries:
  - the target-region diff;
  - exact per-function cost;
  - the instruction to write general, conditional cards with no task names.
- Held-out test: `e2e_heavy_test.jsonl`, fixed before any sampling.
  - 10 of the 19 unused, guard-passing, non-AC heavy tasks (7 OS, 3 NR),
    spread evenly over human Z3 time.
  - AC is excluded because it was 0/24 solved within 1200 s.
  - Caveat: several OS test tasks share the process_manager code base with
    training tasks. That transfer is within a project, which is the realistic
    use case.
- Test arms: base vs base+pair-cards, 2 repeats each (40 episodes). The
  primary metric is paired target-function cost; solve rate and time are
  secondary.
- Expectations:
  - Within-task path variance (p75 max/min 1.5) is large, so with about 6-8
    paired tasks only an effect around 0.8x or stronger could show; p<0.05
    is unlikely.
  - The plausible outcome is a direction: 0.85-1.0x.
  - The cards may also lower the solve rate if they push agents to decompose
    too much.
  - A cost above 1.0x would mean the conditional lesson was mislearned.

## Pair-card learning: results (2026-11-07)

- Sampling: 36 base episodes on the 9 training tasks, $6.36, 25 new verified
  proofs.
  - Training pairs at 1.5x or more: 7 heavy (4 at 3x or more) and 6 from the
    small train split.
  - Test and val tasks were excluded.
- Cards (`skills/pair_cards.md`, a single DeepSeek call, about $0.04), 6 in
  total:
  - library lemmas over manual pointwise reasoning;
  - a narrow helper that reveals an invariant once;
  - split a large wf conjunction that must be re-established;
  - constructor case analysis for disjunctive transitions;
  - bind old-state facts before mutation;
  - direct per-element loop invariants.
  - All are general and conditional, with no task names.
- Card audit before testing: the decomposition card cites 3 pairs, but the
  full sample spread supports it on only 1 task (new_endpoint).
  - block_running_thread: decomposed proofs cost 8.8M, 15.7M and 20.8M.
  - run_blocked_thread: no relation.
  - Contrasting only the extremes (cheapest vs costliest) overstates a pattern.
    This is a weakness of the pair method.
- Held-out test: 10 tasks × {base, paircards} × 2, 40 episodes, $6.94.
  - Solves: 9/20 vs 9/20. 5 tasks were never solved; all 3 NR test tasks
    timed out in every run.
  - Paired cost on the only 4 tasks solved in both arms: 0.994x (p=1.0).
    2 of those 4 give identical cost in every run of both arms (essentially
    one proof).
  - One sibling task of a training task (block_running..._set_trap_frame) was
    solved 2/2 with cards vs 0/2 base. It is a single task, so no claim is
    made.
- Verdict: no measurable effect, inside the expected 0.85-1.0 range at the
  null end. Same-task pair cards did no better than hand rules.

## Updated conclusions

- Proof-cost knowledge stated as text did not let DeepSeek predict which
  statements are unneeded-and-costly better than chance: no guidance, the
  evidence-based rules and the learned cards all failed. The learned cards
  overfit train idioms.
- What works is measurement-in-the-loop: exact-rlimit search finds 22% savings
  on heavy proofs and about 4% on small ones, without an LLM.
- Implication for the proof-time-as-reward plan: the reward must come from the
  verifier measurement (search, or RL/selection with rlimit feedback), not from
  static textual skills. A promising cheap combination: LLM proposes and the
  measurement decides. Use exact rlimit as a selection/reward signal among
  multiple candidate proofs or edits.
- Not yet tested: whether rules change what an agent WRITES from scratch, which
  needs a heavy-task solving harness. The current runners exclude OS/NR and
  need Lynette, which is unavailable here.

## Conclusions so far (earlier, before follow-up)

- Solid:
  - The metric and method (exact replayed rlimit plus a seconds check).
  - On these tasks, cost is driven by definition unfolding, prelude axioms and
    case splitting, not by redundant plain asserts or user quantifiers.
  - Large, real savings exist on heavy proofs and come from one specific
    statement: an unneeded assertion of a large predicate. `spinoff_prover`
    context isolation is a second lever.
- Not established:
  - Whether an agent can learn to *avoid writing* such assertions.
  - Whether learned guidance transfers.
  - Every large saving so far comes from deletion found by exhaustive search,
    which an LLM is not needed for.
- On small tasks (AL/IR/AC-light), proof time is not a meaningful objective:
  solver time is milliseconds and 1% of episode time.

## Decision / Next step

- Do NOT run DeepSeek card learning yet. Current contrast packets would mix
  multi-edit diffs with mostly null effects, and val (17 tasks, single runs) has
  no statistical power.
- Candidate next steps, to discuss with the user/advisor:
  - (a) Build an evidence-backed rule set: "avoid asserting large predicates
    not needed by the goal; prefer one lemma call over pointwise reasoning;
    consider spinoff for large contexts". Test whether DeepSeek
    *writing/repairing heavy proofs* with these rules produces cheaper proofs
    at equal success. Heavy tasks need the actual heavy-project solving setup.
  - (b) Treat cheap search (single-statement deletion plus spinoff toggling,
    verified by exact rlimit) as a post-processing tool and as a source of
    clean single-factor contrast pairs for skill learning.
  - (c) Use the rlimit/QI reward only where solver time matters (AC/OS/NR
    heavy tasks).

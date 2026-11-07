# Proof time as metric and skill-learning reward: stage summary report

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-11-07T13:50:58`
- status: `final_stage_summary`
- audience: advisor and group meeting
- assignment: `../../meetings/20261106-150340-proof-time-as-evaluation-metric-and-skill-learning-reward-meeting/ENTRY.md`
- full evidence: `../../experiments/20261106-160045-verus-proof-time-measurement-and-proof-speed-learning-study/ENTRY.md`
- code: `scripts/proof_time/` (commits `49e4f7a`, `be2dce5`)
- run outputs: `$VERUS_SKILL_RUN_ROOT/proof-time-study-20261106/` (not committed)

## Question

The 2026-11-06 meeting asked whether Verus proof (solver) time can serve as an
evaluation metric beside tokens, and as a reward for learning contextualized
skills. This splits into four questions:

1. How do we measure proof cost reliably?
2. What makes a Verus proof expensive?
3. How much can be saved?
4. Can an agent (DeepSeek V4 Pro) learn to write cheaper proofs?

## One-paragraph answer

Exact Z3 resource count (rlimit), obtained by replaying the SMT log, is a
deterministic and reliable cost metric. Cost on heavy tasks is driven by
definition unfolding and case splitting, and the largest avoidable cost is an
assertion of a large predicate the proof does not need. Measurement-driven
search removes about 22% of the cost of heavy human proofs (4% on small ones),
and an agent that runs a cost tool and cleans up after verification gets about
13% on heavy tasks. Text skills, whether hand-written rules or cards learned
from contrasts, did not measurably change the cost of what DeepSeek writes on
heavy tasks. Proof cost therefore works as a measurement, selection and reward
signal, but it does not compress into static text guidance.

## 1. Measurement

- Verus 0.2025.09.12's built-in per-function `rlimit-count` is wrong: each
  function is charged the previous query's cost, and the last query of each
  context is never counted (e.g. a 142 s query reported as 60,891 instead of
  99,031,273).
- `scripts/proof_time/smt_replay.py` fixes this: log SMT, add
  `(get-info :all-statistics)` after each `check-sat`, replay in the bundled
  Z3 4.12.5, attribute per function.
- Exact rlimit is seed-stable (median max/min 1.000, p90 1.004), while wall
  and SMT seconds vary 5-18%.
- rlimit tracks real time: log-log correlation 0.86 with Z3 time across 68
  heavy tasks. 48/49 variants with rlimit ratio < 0.8 were confirmed in
  seconds (median SMT-time ratio 0.72).
- Recommendation: use exact rlimit (plus quantifier instantiations) as the
  metric; report seconds only as confirmation.

## 2. What drives proof cost

- Benchmark-wide (802 human proofs): median wall time 0.64 s; only 12% of
  tasks spend more than 1 s in SMT. Heavy tasks are concentrated in AC, OS
  and NR. On small tasks, solver time is milliseconds and about 1% of agent
  episode time, so proof time is not a meaningful objective there.
- DeepSeek proofs are not systematically slower than human proofs
  (geometric mean 1.03 on 50 fixture tasks).
- On heavy proofs, quantifier instantiations come mostly from spec-function
  unfolding (median 42%) and Verus prelude axioms (14%); user quantifiers are
  7%. No matching loops were found.
- Single-factor ablation (1,392 variants on 68 heavy proofs): most single
  deletions change nothing, but in 13/68 tasks one change cuts cost by more
  than 30%. The mechanism (confirmed by QI profiles): asserting an unneeded
  large predicate (`wf()`, a transition predicate, a big `forall`) creates an
  obligation whose discharge unfolds definitions and case-splits.
  `#[verifier::spinoff_prover]` is a second lever (best 0.25x), but it hurts
  small proofs.
- "Bad habits" (duplicated asserts, extra `broadcast use`, unscoped
  `assert by`) cost 0-3%.
- Failing proofs: errors before SMT take 0.19 s; failing calls are about 25%
  faster than passing ones. On heavy proofs, a missing needed fact often makes
  the solver run long instead of failing fast.

## 3. How much can be saved

| Method | Tasks | Cost ratio (geomean) | Notes |
|---|---|---|---|
| Exact-rlimit search post-processor, no LLM | 67 heavy human proofs | 0.781 | 23 tasks save >20%; all confirmed on other seeds |
| Same search | 50 small DeepSeek proofs | 0.958 | little removable cost |
| DeepSeek optimizer, 4 rounds | 33 small train tasks | 0.956 | many failed rounds |
| Agent with cost tool + cleanup procedure | 14 val tasks (small) | 0.952 (p=0.18) | 1.40x agent time |
| Agent with cost tool + cleanup procedure | 9 heavy tasks | 0.868 (p=0.16) | 1.24x agent time (p=0.046) |

- Real-seconds examples: 30.2 s -> 10.8 s (NR, one deleted
  `assert forall`), 9.7 s -> 3.8 s (AC, spinoff).
- Agent example: on `run_blocked_thread`, base wrote a 23.1M proof; the
  procedure agent found a different 8.4M path and then removed about 30
  asserted large predicates using its cost tool, reaching 4.6M.

## 4. Can an agent learn to write cheaper proofs?

All end-to-end runs used the real Codex CLI driving DeepSeek V4 Pro (effort
max) under a bwrap sandbox, with exact final cost of the target function plus
any helpers the proof added. Paired comparisons use per-task medians over
solved repeats with a sign-flip permutation test.

| Skill tried | Where learned | Test | Cost vs base |
|---|---|---|---|
| none (just ask to rank costly statements) | - | 30 held-out heavy proofs, ranking | precision@5 0.258 vs random 0.196 |
| learned cards from single-statement contrasts | train split | same ranking test | 0.217 (worse than none; fit train only) |
| rules (evidence rules + small-task cards) | ablations + train labels | val 20 small tasks, 240 episodes | 0.972, p=0.029 (14 paired tasks) |
| rules | same | 16 heavy tasks, 75 episodes | 1.036, n.s. |
| cards learned from same-task cheap/costly proof pairs | 9 heavy + small train tasks | 10 held-out heavy tasks, 40 episodes | 0.994, p=1.0 (4 paired tasks); solves 9/20 vs 9/20 |

Why text skills fail here:

- Whether a statement is costly depends on context: the same "assert the wf
  conjuncts" helps when the obligation must be re-proved and hurts when it is
  not needed. Only running the solver tells which case applies.
- On heavy tasks, variation between solution paths of the same task (p75
  max/min 1.5x, up to 4x) is larger than any skill effect, so a small effect
  would also be hard to detect.
- Learning from the cheapest-vs-costliest pair overstates patterns: the
  decomposition card cited 3 pairs but the full sample supported it on only 1
  task.

## Recommendation for the skill-learning project

- Use exact rlimit as a reward or selection signal computed by the verifier,
  not as content for static skills:
  - best-of-k selection among verified candidates (path variance is large, so
    this is cheap and effective on heavy tasks);
  - a post-verification cleanup step or tool (search, or the agent's own
    cost-guided edits);
  - RL or preference data where the reward includes measured cost.
- Restrict proof-time objectives to solver-heavy domains (AC/OS/NR-like
  code). On small tasks it adds noise to the token/solve metrics without
  practical benefit.
- Possible integration: report `smt_replay` cost as a secondary metric in the
  existing card evaluation. It needs only the final proof and costs one
  replay per proof. To discuss with the group before building.

## Caveats

- Heavy end-to-end tests are small (9 and 4 paired tasks); the procedure's
  0.87x is a direction, not a significant result.
- AC tasks were never solved within 1200 s, so heavy results cover OS and NR
  only.
- The `rules` text was written partly from ablations on human proofs of some
  heavy tasks (a mild leak in its favour; it still showed no effect).
- The 240 val episodes ran before the sandbox fix; an audit found no episode
  opened its own target's answer.
- The fixture test-20 was not used.

## Cost

- DeepSeek spend: about $60 for the ranking evaluation (2026-11-06; the key
  may be shared), $40 for the val A/B, $18 for the heavy A/B, $13.3 for pair
  cards (about $31 on 2026-11-07). All end-to-end runs used off-peak pricing.

## Decision / Next Step

- The direction is at a stopping point. Bring this summary to the advisor.
- Optional if requested: run the procedure and pair-card arms on test-20
  (about $13), or build the `smt_replay` metric hook for the card evaluation.

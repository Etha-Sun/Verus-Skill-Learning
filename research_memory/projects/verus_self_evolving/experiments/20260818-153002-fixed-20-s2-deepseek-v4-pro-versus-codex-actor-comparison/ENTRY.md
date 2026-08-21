# Fixed-20 S2 DeepSeek V4 Pro versus Codex actor comparison

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-08-18T15:30:02`
- status: `complete_bounded_600s`
- dataset/split: all 20 tasks in the frozen fixed-selection (`val`) split,
  manifest SHA-256
  `7d0dc9b2cc74222638f938df2f2f4a1eafbdbfdce536c1fcc6a319d4bcb83453`
- shared skill: accepted S2/final skill, SHA-256
  `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e`
- conditions: fresh `deepseek-v4-pro` actor and fresh local-quota
  `gpt-5.6-sol` actor
- shared harness: Codex CLI native Responses, max reasoning, 1,048,576-token
  configured context, 600-second task endpoint, independent Verus plus Lynette
  hard judgment
- concurrency: conditions execute sequentially; each phase uses 20 workers, so
  the run never intentionally exceeds 20 simultaneous actor tasks
- retries: no retry for a valid 600-second truncation; at most two clean
  retries for an invalid harness result
- metrics: solved count, Claude-failed subset solved count, paired task
  transitions, fidelity, wall time, token usage, and DeepSeek USD cost
- leakage controls: no reference proof, prior trajectory, optimizer analysis,
  or test item is visible; only the already accepted S2 skill is supplied
- evidence boundary: this is a fresh rerun on a repeatedly used selection set,
  not held-out test evidence and not an estimate of population performance
- cost: no cap; DeepSeek API cost is recorded and Codex is labeled local quota
- stop condition: both conditions produce 20 valid task judgments or the run
  records any residual invalid judgments explicitly

## Commands

```bash
${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed20-s2-pro-vs-codex-20260818-1525/launch.sh
```

## Outputs

- run directory:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed20-s2-pro-vs-codex-20260818-1525/`
- logs: `run.log`, `deepseek_pro/bridge.log`, per-task Codex event logs
- metrics: `summary.json`, `per_task.csv`, `per_task.json`, and
  `deepseek_pro/cost_ledger.json`
- manifest: `run_contract.json`, frozen `skill_s2.md`, bridge manifest, and
  per-task run manifests

## Results

| metric | DeepSeek V4 Pro | Codex / GPT-5.6 Sol | Codex minus Pro |
|---|---:|---:|---:|
| hard solved | 15/20 | 17/20 | +2 |
| normal unsolved | 1 | 1 | 0 |
| valid 600-second truncations | 4 | 2 | -2 |
| historical Claude-failed solved | 2/5 | 3/5 | +1 |
| AC solved | 3/6 | 4/6 | +1 |
| AL solved | 7/7 | 7/7 | 0 |
| IR solved | 5/7 | 6/7 | +1 |

All 15 Pro-solved tasks were also solved by Codex. Of the five Pro-unsolved
tasks, Codex solved two and left three unsolved; the paired transition counts
are 15 S-to-S, 2 U-to-S, 3 U-to-U, and 0 S-to-U. Both actors normally
finished but failed task `cac8c7541d651d3480ff`. Pro timed out on four tasks;
Codex solved two of those and timed out on the other two.

The drained Pro ledger contains 338/338 metered off-peak requests, zero errors,
12,281,127 prompt tokens, 418,854 completion tokens, 12,699,981 total tokens,
and USD 1.357109 estimated cost. Codex used local quota and reported 8,619,981
input tokens, including 7,817,984 cached input tokens, plus 129,787 output
tokens and 70,896 reasoning-output tokens. All 20 results in both conditions
are valid V1/V2 judgments. The 20 frozen source hashes remained unchanged and
the test split was not read.

## Interpretation

Under the shared 600-second endpoint, Codex obtained two more solved tasks than
Pro without losing a Pro-solved task. This is a descriptive paired result on a
repeatedly used selection set, not held-out evidence. It is also time-censored:
four Pro tasks and two Codex tasks reached the endpoint, so the experiment does
not establish an unbounded-runtime capability difference. The user declined a
Pro extended-time rerun and asked the original Codex phase to finish; no
extended-time rerun is included.

## Next Action

Do not rerun DeepSeek for this comparison. If the two remaining Codex censored
cases become decision-relevant, predeclare an extended-time follow-up and keep
it separate from this bounded result. For future SkillOpt optimization, retain
the fast-update trajectory minibatches of eight; redesign slow update before
another large run because its current optimizer call consumes all 20
longitudinal pairs at once.

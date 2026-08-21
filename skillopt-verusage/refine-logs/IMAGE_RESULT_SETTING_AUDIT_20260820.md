# Image Result and Setting Audit

Date: 2026-08-20

## Clarification Received After the Initial Audit

The screenshot author confirms that the reported runs used the July Verus and
compared `no-skill` with a `baseline/native skill`. This is not established to
be our accepted S2. The likely native seed is the 838-byte
`skillopt-verusage/skills/initial.md` with SHA-256 `96a55758...`; our test
comparison used the 4,179-byte evolved S2 with SHA-256 `15496115...`. The exact
baseline hash is still required. Unless it equals the S2 hash, the screenshot's
second column and our S2 column are different treatments.

Consequently, the official-Verus two-task rerun below corrects our blank/S2
grid, not the screenshot author's no-skill/baseline grid. The baseline-skill
versions of questions 9 and 19 still require a fresh aligned rerun.

The reported question numbering matches our frozen order: question 9 is
`f24cf9...` and question 19 is `826687...`. This, plus exact agreement on the
GPT and DeepSeek no-skill scores, is evidence that the task set is probably
aligned, although the full manifest hash remains the definitive check.

## Author-Reported July-Verus Results

Because questions 9 and 19 fail before useful proof feedback under July Verus,
the fixed-set score remains `/20`, while `/18` is useful only as a secondary
diagnostic showing performance on the legacy-scoreable remainder.

| Actor | No skill | Baseline skill | Delta | No skill on remaining 18 | Baseline on remaining 18 |
|---|---:|---:|---:|---:|---:|
| DeepSeek V4 Pro | 13/20 | 15/20 | +2 | 13/18 | 15/18 |
| Qwen3.8-27B FP8 | 5/20 | 4/20 | -1 | 5/18 | 4/18 |
| GPT-5.6 Sol Max | 18/20 | 17/20 | -1 | 18/18 | 17/18 |
| GLM-5.3 | 16/20 | 16/20 | 0 | 16/18 | 16/18 |

Qwen has one gain (question 4), two regressions (questions 6 and 7), and only
three tasks solved in both conditions. GPT has one stated regression
(question 11, timeout) and 17 common successes. DeepSeek's and GLM's complete
paired gain/regression matrices are still needed; equal or improved aggregate
scores do not prove that the same tasks were retained.

Efficiency claims must distinguish two estimands. Mean time/cost over all 20
tasks captures the operational cost of regressions and timeouts. Mean over the
intersection of solved tasks is a conditional diagnostic and must report its
sample size; for Qwen that sample is only three tasks. Comparing each arm's
separate solved subset would be composition-biased, especially when the skill
changes which tasks solve.

## Bottom Line

The old verifier was one real source of undercounting, but it is not enough to
explain the full gap to `WechatIMG221.jpg`. Fresh actor reruns with the official
VeruSAGE Verus commit solve
`f24cf9cc9db98c56f792` in every completed GPT, DeepSeek, and GLM condition;
`826687f9c56eb8e65d5d` remains unsolved at 600 seconds in all six conditions.
Replacing only these two version-sensitive outcomes raises every completed
blank/S2 result by one task.

The largest remaining discrepancy is GLM. The stable worker-2 runs still
experienced provider throttling, and the two-task official-Verus reruns
recorded 17 and 21 recovered HTTP 429s. Backoff consumed 193 and 372 aggregate
thread-seconds inside the fixed task budgets. Therefore the current GLM
12/20 results are throughput-confounded rather than clean capability estimates.
Across the complete stable July-Verus runs, GLM blank/S2 actually accumulated
235/241 recovered HTTP 429s and 2,865/2,322 aggregate thread-seconds of
backoff. This averages 143/116 seconds per task. Subtracting only that waiting
from our 361/296-second mean wall times gives 217/180 seconds, close to the
screenshot's 225/207 seconds. Unsolved tasks averaged 260/208 seconds of
backoff, versus 66/55 seconds for solved tasks, directly linking throttling to
the lower score.

## Screenshot Versus Our July-Verus Results

The screenshot does not include a machine-readable contract. Its second skill
is labeled `Native baseline`, while ours is the hash-locked accepted S2. The
comparison below is provisional until the screenshot run supplies the exact
test IDs and hashes.

| Actor | Image no skill | Our blank | Gap | Image second skill | Our S2 | Gap |
|---|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | 18/20 | 18/20 | 0 | 17/20 | 17/20 | 0 |
| DeepSeek V4 Pro | 13/20 | 13/20 | 0 | 15/20 | 13/20 | -2 |
| GLM-5.3 | 16/20 | 12/20 | -4 | 16/20 | 12/20 | -4 |
| Qwen3.8-27B FP8 | 5/20 | pending | -- | 4/20 | pending | -- |

The screenshot's mean wall times are lower for every shared completed actor:

| Actor | Image blank / second skill | Ours blank / S2 |
|---|---:|---:|
| GPT-5.6 Sol | 148 / 190 s | 206 / 206 s |
| DeepSeek V4 Pro | 287 / 283 s | 370 / 341 s |
| GLM-5.3 | 225 / 207 s | 361 / 296 s |

Our DeepSeek runs had 7 and 8 valid task timeouts. Our stable GLM runs had 7
and 6. The uniformly longer wall time and GLM's recovered throttling support a
common execution-budget/throughput difference; they do not support attributing
the whole gap to model quality.

## Two Verus Reporting Versions

For our blank/S2 grid, Version A is the immutable historical result under local Verus
`0.2025.07.12.0b6f3cb`, where the two alias-sensitive items count as failures.
Version B is a targeted official-toolchain correction: keep the other 18
historical task outcomes and replace the two affected outcomes with fresh actor
runs under official VeruSAGE commit
`ddc66116aa7a844a9e19cc50922fe85c84b8b4a5`.

| Actor | Version A blank | Version A S2 | Version B blank | Version B S2 |
|---|---:|---:|---:|---:|
| GPT-5.6 Sol | 18/20 | 17/20 | 19/20 | 18/20 |
| DeepSeek V4 Pro | 13/20 | 13/20 | 14/20 | 14/20 |
| GLM-5.3 | 12/20 | 12/20 | 13/20 | 13/20 |
| Qwen3.8-27B | pending | pending | pending | pending |

Version B is not a fresh 20-task rerun. It is the requested two-task targeted
correction and must be labeled as such. A publication-grade official-toolchain
number requires rerunning all 20 tasks in each condition. Qwen was not run
because the available four-GPU vLLM service belongs to another user; it was
not used or modified.

An offline re-verification of the old candidates produced GPT 19/17,
DeepSeek 13/13, and GLM 12/13. Fresh reruns are higher in several cells because
the actor can now receive meaningful verifier feedback. This is why merely
rescoring old candidates is a lower bound, not a replacement for rerunning the
affected tasks.

## Fresh Two-Task Rerun

All six conditions used the same frozen test manifest, prompt hash, skill
hashes, Codex CLI actor, 262,144-token context, 600-second task budget, and the
official Verus binary with SHA-256
`737048da2e41eabe9b3b0594edb11da6593358b8d55f8dcd270de539acd66e2d`.

| Actor | Skill | Solved | `f24...` | `826...` | Cost |
|---|---|---:|---|---|---:|
| GPT-5.6 Sol | blank | 1/2 | solved, 152 s | timeout, 602 s | local quota |
| GPT-5.6 Sol | S2 | 1/2 | solved, 108 s | timeout, 602 s | local quota |
| DeepSeek V4 Pro | blank | 1/2 | solved, 394 s | timeout, 601 s | $0.147638 |
| DeepSeek V4 Pro | S2 | 1/2 | solved, 276 s | timeout, 601 s | $0.162919 |
| GLM-5.3 | blank | 1/2 | solved, 432 s | timeout, 601 s | $0.642495 |
| GLM-5.3 | S2 | 1/2 | solved, 359 s | timeout, 602 s | $0.994141 |

New metered spend was $1.947193: $0.310558 for DeepSeek and $1.636636
for GLM. GPT used local quota. All 12 results were valid, with no terminal
provider error.

## Confirmed and Unresolved Setting Differences

| Setting | Our runs | Screenshot | Assessment |
|---|---|---|---|
| Test identity | 20 IDs, manifest SHA `81194e9c...` | only says 20 tasks | unresolved and first-order |
| Second skill | S2 SHA `15496115...` | `Native baseline` | unresolved and first-order |
| Task prompt | SHA `13a4598f...` | not shown | unresolved |
| Verus | July historically; official `ddc66116` for reruns | not shown | July mismatch confirmed to cost one task |
| Harness | Codex CLI 0.146.1 | not shown | unresolved |
| Task timeout | 600 s, no valid-timeout retry | not shown | likely important |
| Concurrency | GPT/DeepSeek 20 historically; stable GLM 2 | not shown | GLM remains throttled even at 2 |
| Reasoning | GPT max; DeepSeek bridge sends high; GLM sends max plus temperature 1.0 | only GPT is labeled max | not semantically identical |
| Qwen precision | our formal arms pending | FP8 in image | not a controlled comparison |
| Cost basis | complete bridge ledger and current price tables | average basis/rates not shown | costs are not directly comparable |

The launcher records `max` for every model, but the DeepSeek bridge currently
maps its upstream request to `reasoning_effort=high`; GLM sends max reasoning
with `temperature=1.0`. This does not invalidate blank-versus-S2 parity within
one actor, because both skill arms use the same mapping. It does invalidate a
literal claim that every upstream provider received the same `max` setting.

At only 20 tasks, small score differences also have wide uncertainty. For
example, Wilson 95% intervals are approximately 43%-82% for 13/20 and 53%-89%
for 15/20. The DeepSeek two-task gap cannot establish a reproducible setting
effect without repeated paired runs.

## Recommended Next Contract

1. Require the screenshot run to export test IDs/hash, skill bytes/hash, task
   prompt hash, Verus and Codex hashes, actual upstream reasoning/sampling
   parameters, timeout, workers, and retry/cost basis before merging tables.
   In particular, determine whether `baseline/native skill` is `initial.md` or
   another file; do not relabel it S2 without matching SHA-256.
2. For GLM, use one task worker or a global request-rate limiter and calibrate
   until recovered 429 waiting is negligible. Then rerun both full test-20
   skill conditions; do not compare 12/20 directly with 16/20 before this.
3. For final official results, rerun the complete 20-task grid under
   `ddc66116`; retain the targeted Version B table only as an interim corrected
   estimate.
4. Run Qwen only on an owned/released service and lock model revision,
   precision, context, reasoning template, and maximum sequence count.

## Durable Artifacts

- image: `WechatIMG221.jpg`
- offline official-Verus rescore:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/verusage-verus-ddc66116-rescore-20260820/`
- fresh two-task runs:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/official-two-{gpt,deepseek,glm}-{blank,s2}-20260820/`
- driver logs:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/verusage-official-two-task-rerun-20260820/`

Raw and sealed datasets were read only. Generated traces and complete ledgers
remain below `VERUS_SKILL_RUN_ROOT`.

# SkillOpt VeruSAGE Epoch 1: DeepSeek V4 Pro Actor + Codex Sol Optimizer

Date: 2026-08-13

## Contract

- Frozen split: 40 train / 20 selection / 40 held-out test, split SHA
  `53059264e5d0458e1fc50a3c1786cbeac6c671aedf56dd71fb32843b24d2c553`.
- Actor: `deepseek-v4-pro` through Codex CLI and DeepSeek native Responses,
  reasoning effort `max`.
- Optimizer: local Codex `gpt-5.6-sol`; the observed optimizer commands used
  reasoning effort `max`.
- Epoch: selection baseline 20, training rollout 40, native SkillOpt
  reflection/merge/ranking, candidate selection gate 20.
- Concurrency: 20 baseline, 40 training, 20 gate.
- Per-task timeout: 1,200 seconds, with best-workspace preservation and up to
  two clean retries for invalid fidelity only.
- Cost limit: none. Held-out test: not run.
- Run pointer:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-0813-max-sol-e1-20260813`.

## Result

| Stage | Solved | Rate | Interpretation |
|---|---:|---:|---|
| Initial skill, fixed selection S0 | 16/20 | 80.0% | Gate baseline |
| Initial skill, train rollout | 35/40 | 87.5% | Optimizer evidence only |
| Candidate skill, same selection set | 17/20 | 85.0% | Accepted: strict improvement over 80.0% |

The paired selection transition was 1 fail-to-pass, 0 pass-to-fail, 16
pass-to-pass, and 3 fail-to-fail. The initial skill was 838 bytes, SHA
`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`.
The accepted candidate is 2,932 bytes, SHA
`b94eb236264e39aa114227a65a93802348ece048ff084819974faa478ba5227c`.
SkillOpt selected and applied 4 of 12 merged edits.

This is a selection-gate result, not held-out evidence. It does not establish
that the candidate improves population solved rate or token efficiency.

## DeepSeek actor cost

The table records actual paid traffic, including retries and the early
fidelity-audit retry overhead. `Reasoning output` is a subset of output and is
not added again when computing cost.

| Phase | Final task results | Solved | Paid task attempts | API requests | Cache-hit input | Cache-miss input | Output | Reasoning output | Cost (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Selection S0 | 20 | 16 | 35 | 1,190 | 62,473,856 | 958,737 | 1,073,458 | 865,257 | 1.577426783 |
| Train rollout | 40 | 35 | 40 | 1,461 | 82,913,664 | 937,828 | 1,148,101 | 880,357 | 1.707365082 |
| Candidate gate | 20 | 17 | 22 | 908 | 49,226,496 | 596,277 | 764,677 | 591,089 | 1.103095533 |
| **Formal epoch total** | **80** | - | **97** | **3,559** | **194,614,016** | **2,492,842** | **2,986,236** | **2,336,703** | **4.387887398** |

Total actor input was 197,106,858 tokens. Cost uses the recorded 2026-08-13
DeepSeek V4 Pro rates: USD 0.003625/M cache-hit input, USD 0.435/M cache-miss
input, and USD 0.87/M output.

## Local optimizer usage

| Stage | Calls | Input tokens | Output tokens | Total tokens | Metered cash cost |
|---|---:|---:|---:|---:|---:|
| Analyst | 6 | 906,180 | 23,469 | 929,649 | USD 0 |
| Merge | 2 | 38,449 | 5,964 | 44,413 | USD 0 |
| Ranking | 1 | 18,450 | 284 | 18,734 | USD 0 |
| **Optimizer total** | **9** | **963,079** | **29,717** | **992,796** | **USD 0** |

The optimizer used local Codex quota. A USD 0.444793 DeepSeek-rate equivalent
is retained only as a counterfactual estimate with all optimizer input treated
as cache miss; it was not billed and is not included in the formal cash total.

The Pro-native preflight (USD 0.059688177) and the stopped wrong-reasoning
startup (USD 0.288416600) are excluded from the formal epoch table. Including
those bring-up calls, this Pro launch consumed USD 4.735992175. This figure
does not include older Flash, calibration, retrieval, or unrelated runs.

## Integrity and caveats

- All 80 final task results completed: 77 `V2_TRACE`, 3 `V1_TRUNCATED`, and
  zero `V0_INVALID`.
- Ten final tasks reached the 1,200-second timeout; the harness preserved and
  independently judged the best candidate instead of discarding the task.
- All 3,559 provider requests used native Responses pass-through with upstream
  model `deepseek-v4-pro`; provider errors: zero.
- All 80 source inputs passed the independent unchanged-input check.
- No held-out test directory or result was produced.
- An audit fix made temporary-copy experiments such as editing
  `/tmp/.../candidate.rs` non-invalidating while continuing to reject shell
  writes to the formal workspace `candidate.rs`.
- Raw source data and sealed data remained read-only. Generated outputs stayed
  below `VERUS_SKILL_RUN_ROOT`.

# SkillOpt on VeruSAGE Experiment Tracker

状态：`PLANNING COMPLETE / NO MODEL RUNS LAUNCHED`

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| SV-P00 | Planning | pin upstream | SkillOpt commit `9639719` | n/a | clean checkout | MUST | COMPLETE | clone only; no upstream edits |
| SV-P01 | Planning | inspect compatibility | SkillOpt + VeruSAGE + local fidelity harness | n/a | interface map | MUST | COMPLETE | scalar gate and ungated slow-update risk identified |
| SV-P02 | Planning | freeze proposal | MVP design | n/a | claim/stop-go audit | MUST | COMPLETE | no experiment result claimed |
| SV-M0-UNIT | M0 | adapter contract | synthetic/model-free | fixture | path, hash, score, redaction, safety veto, request cap | MUST | TODO | test timeout/rate-limit/not-found paths |
| SV-M0-CONFIG | M0 | reject unsafe defaults | frozen YAML audit | fixture | slow gated; meta/density off; external out root | MUST | TODO | fail closed |
| SV-M0-SPLIT | M0 | freeze 40/20/40 tasks | deterministic effective-train split | 100-task dev set | overlap and sealed-read audit | MUST | TODO | static provenance only; freeze before new VeruSAGE outcomes |
| SV-M1-GPT-H0 | M1 | GPT no-skill fidelity/cost smoke | GPT-5.5/high VeruSAGE H0 | one D_train task | V3, Verus, Lynette, usage, cache ratio | MUST | TODO | max attempts 2; stop if cost > USD 1.25 |
| SV-M1-GPT-S0-A | M1 | GPT skill injection smoke | seed skill S0 | same task | call-level skill/prompt hashes, usage | MUST | TODO | fresh workspace |
| SV-M1-GPT-S0-B | M1 | GPT A/A variability | seed skill S0 repeat | same task | outcome/token dispersion | MUST | TODO | do not optimize |
| SV-M1-GPT-COST | M1 | GPT cost spread | VeruSAGE H0 | two additional static code-length buckets | usage, cache ratio, requests | MUST | TODO | three distinct H0 tasks total |
| SV-M1-DS-H0 | M1 | DeepSeek no-skill fidelity/cost smoke | DeepSeek-V4-Pro thinking VeruSAGE H0 | one D_train task | V3, Verus, Lynette, usage, cache ratio | MUST | TODO | max attempts 2; stop if cost > USD 0.55 |
| SV-M1-DS-S0-A | M1 | DeepSeek skill injection smoke | seed skill S0 | same task | call-level skill/prompt hashes, usage | MUST | TODO | fresh workspace |
| SV-M1-DS-S0-B | M1 | DeepSeek A/A variability | seed skill S0 repeat | same task | outcome/token dispersion | MUST | TODO | do not optimize |
| SV-M1-DS-COST | M1 | DeepSeek cost spread | VeruSAGE H0 | two additional static code-length buckets | usage, cache ratio, requests | MUST | TODO | three distinct H0 tasks total |
| SV-M2-BASE | M3 | selection baseline | S0 | D_sel | composite gate + raw SSR/ETtS | MUST | TODO | SkillOpt baseline evaluation |
| SV-M2-E1 | M3 | epoch 1 bounded update | S1 candidate | 40 D_train + 20 D_sel | accepted/rejected edit | MUST | TODO | edit budget 4; minibatch 8 |
| SV-M2-E2 | M3 | epoch 2 bounded update | S2 candidate | 40 D_train + 20 D_sel | accepted/rejected edit | MUST | TODO | cosine edit budget reaches 2 |
| SV-M2-SLOW-E2 | M3 | gated longitudinal update | previous/current/slow candidate | 20+20 D_train + 20 D_sel | longitudinal pairs, accepted/rejected guidance | MUST | TODO | mixed policy; never force accept |
| SV-M2-FREEZE | M3 | freeze validation-best | S_best | n/a | skill/hash/version provenance | MUST | TODO | distinguish best from final |
| SV-M3-ONESHOT | M4 | isolate iterative loop | S_one_shot | D_train only | schema, safety, length | MUST | TODO | no D_sel/D_test visibility |
| SV-M4-H0 | M5 | original scaffold baseline | H0 | 40 D_test | SSR, ETtS, safety | MUST | TODO | fresh VeruSAGE run; historical Codex H0 is cost prior only |
| SV-M4-S0 | M5 | seed prompt baseline | S0 | 40 D_test | SSR, ETtS, safety | MUST | TODO | trainer internal baseline test |
| SV-M4-ONESHOT | M5 | one-shot control | S_one_shot | 40 D_test | SSR, ETtS, safety | MUST | TODO | fresh run |
| SV-M4-BEST | M5 | main method | S_best | 40 D_test | SSR, ETtS, safety | MUST | TODO | frozen validation-best skill only |
| SV-M4-FINAL | M5 | conditional last-skill audit | S_final | 20 D_sel + 40 D_test | final-vs-best divergence | CONDITIONAL | BLOCKED | only if final hash differs from best; at most 60 rollouts |
| SV-M4-E4 | M5 | paper-default epoch confirmation | 4 epochs, slow + meta | same 40/20/40 | paired direction and cost | CONDITIONAL | BLOCKED | new frozen run only after 2-epoch GO |
| SV-M5-GATE | M6 | rejected-update audit | rejected candidates | D_sel | solve/cost/safety reason | NICE | TODO | no new model calls |
| SV-M5-FAIL | M6 | mechanism analysis | H0/S0/one-shot/best | all valid runs | error/action/loop/token | MUST | TODO | unknown attribution remains explicit |
| SV-M5-CLOSE | M6 | reviewed closeout | compact summary | n/a | claim boundary and data safety | MUST | TODO | update research memory and index |

## Frozen planning budget

| Arm | Two-epoch complete matrix | Optimizer | Hard approval cap | Status |
|---|---:|---|---:|---|
| GPT | 360-420 target task rollouts; 16-22 optimizer logical calls | GPT-5.5 | USD 500 | BLOCKED on M0/M1 |
| DeepSeek | 360-420 target task rollouts; 16-22 optimizer logical calls | GPT-5.5 shared for target-model isolation | USD 250 | BLOCKED on M0/M1 |

Both arms together require 720-840 main target task rollouts, plus 5
fidelity/cost rollouts per arm. The target provider hard cap is 12 requests per rollout.
Four-epoch confirmation is not pre-approved; if the two-epoch gate passes,
the proposed caps are USD 850 for GPT and USD 400 for DeepSeek.

## Current next action

Implement `SV-M0-UNIT` only. Do not launch a target or optimizer model until:

1. external output enforcement is tested;
2. the 40/20/40 split and sealed-read guards are frozen;
3. central skill injection has call-level hash coverage;
4. independent final Verus/Lynette, 8k-token reflection compaction, and
   token-ledger tests pass;
5. each arm's three-distinct-task / five-rollout calibration passes;
6. model/API budget is explicitly approved.

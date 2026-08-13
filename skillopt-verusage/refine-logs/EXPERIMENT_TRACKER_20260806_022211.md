# SkillOpt on VeruSAGE Experiment Tracker

状态：`PLANNING COMPLETE / NO MODEL RUNS LAUNCHED`

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| SV-P00 | Planning | pin upstream | SkillOpt commit `9639719` | n/a | clean checkout | MUST | COMPLETE | clone only; no upstream edits |
| SV-P01 | Planning | inspect compatibility | SkillOpt + VeruSAGE + local fidelity harness | n/a | interface map | MUST | COMPLETE | scalar gate and ungated slow-update risk identified |
| SV-P02 | Planning | freeze proposal | MVP design | n/a | claim/stop-go audit | MUST | COMPLETE | no experiment result claimed |
| SV-M0-UNIT | M0 | adapter contract | synthetic/model-free | fixture | path, hash, score, redaction, safety veto, request cap | MUST | TODO | test timeout/rate-limit/not-found paths |
| SV-M0-CONFIG | M0 | reject unsafe defaults | frozen YAML audit | fixture | slow/meta/density off; external out root | MUST | TODO | fail closed |
| SV-M0-SPLIT | M0 | freeze 6/4/4 tasks | deterministic effective-train split | train-only | overlap and sealed-read audit | MUST | TODO | freeze before new H0 outcomes |
| SV-M1-H0 | M1 | no-skill fidelity smoke | VeruSAGE H0 | one D_train task | V3, Verus, Lynette, usage | MUST | TODO | max attempts 2 |
| SV-M1-S0-A | M1 | skill injection smoke | seed skill S0 | same task | call-level skill/prompt hashes | MUST | TODO | fresh workspace |
| SV-M1-S0-B | M1 | A/A variability | seed skill S0 repeat | same task | outcome/token dispersion | MUST | TODO | do not optimize |
| SV-M2-BASE | M3 | selection baseline | S0 | D_sel | composite gate + raw SSR/ETtS | MUST | TODO | SkillOpt baseline evaluation |
| SV-M2-STEP1 | M3 | first bounded update | S1 candidate | D_train + D_sel | accepted/rejected edit | MUST | TODO | edit budget 2 |
| SV-M2-STEP2 | M3 | second bounded update | S2 candidate | D_train + D_sel | accepted/rejected edit | MUST | TODO | edit budget 2 |
| SV-M2-FREEZE | M3 | freeze validation-best | S_best | n/a | skill/hash/version provenance | MUST | TODO | distinguish best from final |
| SV-M3-ONESHOT | M4 | isolate iterative loop | S_one_shot | D_train only | schema, safety, length | MUST | TODO | no D_sel/D_pilot visibility |
| SV-M4-H0 | M5 | original scaffold baseline | H0 | D_pilot | SSR, ETtS, safety | MUST | TODO | fresh run |
| SV-M4-S0 | M5 | seed prompt baseline | S0 | D_pilot | SSR, ETtS, safety | MUST | TODO | fresh run |
| SV-M4-ONESHOT | M5 | one-shot control | S_one_shot | D_pilot | SSR, ETtS, safety | MUST | TODO | fresh run |
| SV-M4-BEST | M5 | main method | S_best | D_pilot | SSR, ETtS, safety | MUST | TODO | frozen skill only |
| SV-M4-REPEAT | M5 | robustness repeat | all four conditions | D_pilot | paired direction | CONDITIONAL | BLOCKED | launch only after first-pass GO |
| SV-M5-GATE | M6 | rejected-update audit | rejected candidates | D_sel | solve/cost/safety reason | NICE | TODO | no new model calls |
| SV-M5-FAIL | M6 | mechanism analysis | H0/S0/one-shot/best | all valid runs | error/action/loop/token | MUST | TODO | unknown attribution remains explicit |
| SV-M5-CLOSE | M6 | reviewed closeout | compact summary | n/a | claim boundary and data safety | MUST | TODO | update research memory and index |

## Current next action

Implement `SV-M0-UNIT` only. Do not launch a target or optimizer model until:

1. external output enforcement is tested;
2. split and sealed-read guards are frozen;
3. central skill injection has call-level hash coverage;
4. independent final Verus/Lynette and token-ledger tests pass;
5. model/API budget is explicitly approved.

# SkillOpt on VeruSAGE Experiment Tracker

状态：`ROBUST EPOCH 1 COMPLETE / PRO REANALYSIS REJECTED BEFORE TARGET GATE`

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| SV-P00 | Planning | pin upstream | SkillOpt commit `9639719` | n/a | clean checkout | MUST | COMPLETE | clone only; no upstream edits |
| SV-P01 | Planning | inspect compatibility | SkillOpt + VeruSAGE + local fidelity harness | n/a | interface map | MUST | COMPLETE | scalar gate and ungated slow-update risk identified |
| SV-P02 | Planning | freeze proposal | MVP design | n/a | claim/stop-go audit | MUST | COMPLETE | no experiment result claimed |
| SV-M0-UNIT | M0 | adapter contract | synthetic/model-free | fixture | path, hash, injection, usage, request cap | MUST | COMPLETE | 13/13 tests + compileall + mypy; includes timeout, 384K escalation, task requeue, phase abort, and process cleanup |
| SV-M0-CONFIG | M0 | reject unsafe defaults | DeepSeek Flash epoch-1 YAML | fixture | slow gated; meta/density off; external out root | MUST | COMPLETE | 40 train / 20 selection / no test |
| SV-M0-SPLIT | M0 | freeze 40/20/40 tasks | deterministic effective-train split | Anvil/IronKV only | overlap and sealed-read audit | MUST | COMPLETE | split SHA `53059264...`; zero overlaps; 20/10/20 tasks per project |
| SV-M1-GPT-H0 | M1 | GPT no-skill fidelity/cost smoke | GPT-5.5/high VeruSAGE H0 | one D_train task | V3, Verus, Lynette, usage, cache ratio | MUST | TODO | max attempts 2; stop if cost > USD 1.25 |
| SV-M1-GPT-S0-A | M1 | GPT skill injection smoke | seed skill S0 | same task | call-level skill/prompt hashes, usage | MUST | TODO | fresh workspace |
| SV-M1-GPT-S0-B | M1 | GPT A/A variability | seed skill S0 repeat | same task | outcome/token dispersion | MUST | TODO | do not optimize |
| SV-M1-GPT-COST | M1 | GPT cost spread | VeruSAGE H0 | two additional static code-length buckets | usage, cache ratio, requests | MUST | TODO | three distinct H0 tasks total |
| SV-M1-DS-H0 | M1 | DeepSeek fidelity/cost smoke | DeepSeek-V4-Flash thinking + S0 | one D_train task | V2, call hashes, Verus, Lynette, usage, cache ratio | MUST | COMPLETE | corrected preflight: one task, one request, USD 0.002534; task unsolved |
| SV-M1-DS-S0-A | M1 | DeepSeek skill injection smoke | seed skill S0 | same task | call-level skill/prompt hashes, usage | MUST | COMPLETE | exact skill hash and delimiter coverage 1/1 |
| SV-M1-DS-S0-B | M1 | DeepSeek A/A variability | seed skill S0 repeat | same task | outcome/token dispersion | MUST | TODO | do not optimize |
| SV-M1-DS-COST | M1 | DeepSeek cost spread | VeruSAGE H0 | two additional static code-length buckets | usage, cache ratio, requests | MUST | TODO | three distinct H0 tasks total |
| SV-M1-DS-CAL8 | M1 | corrected harness calibration | DeepSeek-V4-Flash + S0 | 8 D_train tasks | response integrity, solve, usage, cost | MUST | COMPLETE | 5/8 solved; 267 result-accounted requests; zero silent truncations; USD 0.309593 |
| SV-M2-ROBUST-V1-V4 | M3 | diagnose full-epoch harness | successive corrected variants | D_sel / D_train | dependency, timeout, truncation, cleanup | MUST | INVALID | retained as debug evidence only; no skill-effect claim |
| SV-M2-ROBUST-V5 | M3 | first robust epoch-1 rerun | 60-worker pool; task requeue and fail-closed invalid handling | 20 D_sel + 40 D_train + 20 D_sel | paired hard gate, integrity, usage, cost | MUST | COMPLETE | baseline 6/20; train 8/40; candidate 4/20 and rejected; 80/80 ledgers, zero invalid/silent truncation |
| SV-M2-PRO-V1 | M3 | stronger-optimizer offline reanalysis | Pro analysis + Pro critic; no target rollout | stored 40 D_train trajectories | usage, cost, contract audit | MUST | INVALID | 2 calls; 118,424 input + 3,487 output; USD 0.054548; list serialization and trusted-context semantic failure |
| SV-M2-PRO-V2 | M3 | contract-constrained offline reanalysis | Pro analysis + Pro critic; Flash target frozen | stored 40 D_train trajectories | evidence labels, compactness, cost | MUST | REJECTED | 2 calls; 120,165 input + 6,642 output; USD 0.058050; false Lynette attribution and unsupported one-trajectory rule; no target gate |
| SV-M2-RETRIEVAL-AUDIT | M3 | audit upstream retrieval boundary | research engine + SkillOpt-Sleep | source audit | retrieval stage, unit, default | MUST | COMPLETE | main engine injects whole current skill; Sleep `recall_k` is nightly task-intent Jaccard recall, default 0; no proof-state runtime retrieval |
| SV-M2-BASE | M3 | selection baseline | S0 | D_sel | composite gate + raw SSR/ETtS | MUST | COMPROMISED | observed 0/20, but silent thinking truncation confounds failures |
| SV-M2-E1 | M3 | epoch 1 bounded update | S1 candidate | 40 D_train + 20 D_sel | accepted/rejected edit | MUST | COMPROMISED | 2 strict successes are valid lower bounds; comparative/gate result invalid |
| SV-M2-E2 | M3 | epoch 2 bounded update | S2 candidate | 40 D_train + 20 D_sel | accepted/rejected edit | MUST | TODO | cosine edit budget reaches 2 |
| SV-M2-SLOW-E2 | M3 | gated longitudinal update | previous/current/slow candidate | 20+20 D_train + 20 D_sel | longitudinal pairs, accepted/rejected guidance | MUST | TODO | mixed policy; never force accept |
| SV-M2-FREEZE | M3 | freeze validation-best | S_best | n/a | skill/hash/version provenance | MUST | COMPLETE | best remains 838-byte S0, SHA `96a55758...`; candidate SHA `2ff3f379...` |
| SV-M3-ONESHOT | M4 | isolate iterative loop | S_one_shot | D_train only | schema, safety, length | MUST | TODO | no D_sel/D_test visibility |
| SV-M4-H0 | M5 | original scaffold baseline | H0 | 40 D_test | SSR, ETtS, safety | MUST | TODO | fresh VeruSAGE run; historical Codex H0 is cost prior only |
| SV-M4-S0 | M5 | seed prompt baseline | S0 | 40 D_test | SSR, ETtS, safety | MUST | TODO | trainer internal baseline test |
| SV-M4-ONESHOT | M5 | one-shot control | S_one_shot | 40 D_test | SSR, ETtS, safety | MUST | TODO | fresh run |
| SV-M4-BEST | M5 | main method | S_best | 40 D_test | SSR, ETtS, safety | MUST | TODO | frozen validation-best skill only |
| SV-M4-FINAL | M5 | conditional last-skill audit | S_final | 20 D_sel + 40 D_test | final-vs-best divergence | CONDITIONAL | BLOCKED | only if final hash differs from best; at most 60 rollouts |
| SV-M4-E4 | M5 | paper-default epoch confirmation | 4 epochs, slow + meta | same 40/20/40 | paired direction and cost | CONDITIONAL | BLOCKED | new frozen run only after 2-epoch GO |
| SV-M5-GATE | M6 | rejected-update audit | rejected candidates | D_sel | solve/cost/safety reason | NICE | COMPROMISED | optimizer learned from compact traces with 65/108 empty assistant slots |
| SV-M5-FAIL | M6 | mechanism analysis | H0/S0/one-shot/best | all valid runs | error/action/loop/token | MUST | TODO | unknown attribution remains explicit |
| SV-M5-CLOSE | M6 | reviewed closeout | compact summary | n/a | claim boundary and data safety | MUST | COMPLETE | `CURRENT.md` updated; memory index regenerated; raw run remains external |

## Frozen planning budget

| Arm | Two-epoch complete matrix | Optimizer | Hard approval cap | Status |
|---|---:|---|---:|---|
| GPT | 360-420 target task rollouts; 16-22 optimizer logical calls | GPT-5.5 | USD 500 | BLOCKED on M0/M1 |
| DeepSeek | 360-420 target task rollouts; 16-22 optimizer logical calls | GPT-5.5 shared for target-model isolation | USD 250 | BLOCKED on M0/M1 |

Both arms together require 720-840 main target task rollouts, plus 5
fidelity/cost rollouts per arm. The target provider hard cap is 12 requests per rollout.
Four-epoch confirmation is not pre-approved; if the two-epoch gate passes,
the proposed caps are USD 850 for GPT and USD 400 for DeepSeek.

## Completed epoch-1 ledger

The main Flash-target/Flash-optimizer run contains 20 baseline-selection, 40
training, and 20 candidate-selection task rollouts. Its 358 target calls used 1,594,615 prompt
tokens (1,031,680 cache hit; 562,935 cache miss) and 2,312,040 completion
tokens for USD 0.729071. Eight optimizer calls used 67,128 prompt and 50,702
completion tokens; treating all optimizer prompts as cache misses gives USD
0.023594 and a conservative main-run total of USD 0.752665. Provider smoke and
both task preflights bring the all-in setup-plus-epoch estimate to USD
0.758769 under the same conservative assumption.

This ledger is a valid record of spend, not a valid performance result.
The proxy forced high-thinking calls to 8,192 output tokens: 177/187
exact-cap calls returned no final content, and 69/80 tasks encountered at
least one exact-cap call. The checkout's normal CLI default is 20 repair
steps; this run used 4 and a 12-request hard cap.

## Current next action

Freeze robust v5 as a complete negative epoch-1 result and reject both Pro
reanalyis candidates before target evaluation. A large optimizer output cap was
not binding: Pro v2 used only 6,642 completion tokens across two calls and still
made a verifier-label attribution error. Do not start epoch 2 or held-out test.
The next reviewed pilot should keep the 838-byte seed fixed and evaluate typed,
replay-supported cards with proof-state-conditioned top-1 retrieval plus
abstention; Pro remains an offline card proposer/critic, not an unchecked
global-skill writer.

## Robust v5 epoch-1 ledger

All 80 target task ledgers completed: 20 initial-skill selection, 40 training,
and 20 candidate selection. The target issued 4,184 requests using 35,527,687
prompt tokens (27,766,272 cache hit; 7,761,415 cache miss) and 14,402,537
completion tokens for USD 5.197054. Seven optimizer calls used 112,988 prompt
and 68,942 completion tokens; treating all optimizer prompts as cache misses
gives USD 0.035122 and a combined v5 estimate of USD 5.232176.

The response audit found 34 explicit length limits and one empty response; all
were rejected and recovered (34 at 256K and one same-budget transport retry).
No 384K escalation, provider error, task requeue, `V0_INVALID`, partial ledger,
or silent truncation occurred. The candidate scored 4/20 versus baseline 6/20,
so the best artifact remains the initial skill, SHA
`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`.

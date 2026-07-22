# Hands-Off Trace Distillation Experiment Tracker

旧 IG 路线 R001-R035 已归档在
refine-logs/EXPERIMENT_TRACKER_20260714_163854.md；本 tracker 从 R036
开始。状态枚举：TODO、IN_PROGRESS、DONE、GO、PARTIAL、STOP、BLOCKED、
CONDITIONAL。

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R036 | M0 | corpus inventory | read-only parser | train-candidate metadata only | coverage, duplicates, usage availability | MUST | DONE | 9,383 rows; train 3,347; sealed content reads 0 |
| R037 | M0 | freeze split + leakage audit | exact hash + name + near-duplicate checks | train/dev/test projects | overlap counts, contaminated groups | MUST | DONE | quarantine 6 train traces; final exact/near overlap 0 |
| R038 | M0 | unified hands-off wrapper | Copilot CLI H0/H1/H2 injection | synthetic/task fixture | prompt hash, usage, resume, collision, safety | MUST | DONE | 15 tests total after live-format and timeout regressions; Verus/Lynette pinned |
| R039 | M0 | end-to-end mechanical smoke | H0/H1/H2, 1 non-sealed task each | train-domain smoke | Verus/checker, usage coverage, config diff | MUST | GO | Qwen3.6 mechanical-only: all 3 usage/Verus/Lynette complete; 0/3 solved; context exhaustion exposed |
| R040 | M1 | select train traces | 20-50 de-duplicated successes | AC/AL/IR train only | motif/error/model coverage | MUST | DONE | canonical attempt3: 30 unique verified task/source pairs; 15 Anvil + 15 IronKV; five models ×6; sealed reads 0 |
| R040A | M0.5 | freeze local capability tasks | canonical `unverified/` 30-task selector + physical audit | train calibration, R040-disjoint | task/source/near-overlap, source-fail, paired security validity, tokenizer context, size tertiles | MUST | DONE | canonical attempt4: 15 Anvil + 15 IronKV; small/medium/large each 10; 30/30 paired Verus+Lynette pass; overlap 0; sealed reads 0 |
| R040B | M0.5 | Qwen capability screen | Qwen3.6-27B H0, one repetition | frozen 30-task calibration | security-valid solved, usage, time, verifier/checker, context/tool failure | MUST | DONE | live attempt2 complete: 7/30 pass (23.3%), 11 stalled, 10 infrastructure/timeout, 2 unsafe; 30/30 identities complete; usage 21/30 |
| R040C | M0.5 | stabilize qualitative cases | Qwen H0, two extra repetitions on 3 candidates/class | predeclared R040B candidates | repeated pass/closest_failure/stalled state | MUST | IN_PROGRESS | selection reads H0 only; 18 additional H0 runs maximum; no H1/H2 outcomes viewed |
| R040D | M0.5 | freeze qualitative cases | deterministic pass/closest_failure/stalled selector | R040B-R040C only | first stable task/class, hashes, rationale | MUST | BLOCKED | old near_miss is structurally unreachable because every source has one error; exactly one task/class is qualitative only |
| R041 | M1 | distill prompt variants | H1 generic + H2 trace prompt | train only | prompt tokens, provenance, edit time | MUST | DONE | frozen attempt3: H1 633 tokens, H2 632; delta 0.16%; H2 is one global prompt from 30 R040 traces; transitive provenance and safety review PASS; AI edit 5 min, human 0 |
| R041A | M1 | three-case local contrast | Qwen H0/H1/H2, 3 repetitions | frozen R040D cases | pass retention, closest-failure transition, stalled ceiling | MUST_FOR_C2 | BLOCKED | 3 tasks × 3 conditions × 3 repetitions = 27 records; qualitative, not held-out claim |
| R042 | M1 | reproduce hands-off dev baseline | frontier agent H0 | OS/VE/ST/NO dev | solved, tokens, time, calls, safety | MUST | TODO | same budget as variants |
| R043 | M1 | generic-control dev | frontier agent H1 | same dev tasks | same primary metrics | MUST | TODO | length delta within ±5% |
| R044 | M1 | trace-prompt dev gate | frontier agent H2 | same dev tasks | Δsolved, tokens/solved, paired ratios | MUST | TODO | GO only if plan gate passes |
| R045 | M2 | power/sensitivity update | CPU analysis | frozen baseline + available test | detectable SR margin, required n | MUST | TODO | expand task set if underpowered |
| R046 | M2 | mechanism controls | H1/H4/compressed H2 | dev only | solved-token frontier | MUST | BLOCKED | requires R044 GO/ambiguous signal |
| R047 | M2 | skill-family ablation | H2 leave-one-family-out | dev only | marginal Δsolved/Δtokens | CONDITIONAL | BLOCKED | cut if single prompt sufficient |
| R048 | M2 | retrieval budget sweep | H3 top-k and 100/50/25% budgets | dev only | utility-cost curve, toxicity | CONDITIONAL | BLOCKED | no test access |
| R049 | M2 | freeze final H* | predeclared dev-selected variant | dev only | prompt/hash/config freeze | MUST | BLOCKED | all selections end here |
| R050 | M3 | sealed test baseline | frontier agent H0 | MA/NR or expanded test | all primary outcomes | MUST | BLOCKED | R049 + adequate power required |
| R051 | M3 | sealed test generic control | frontier agent H1 | identical sealed tasks | anti-claim A1 metrics | MUST | BLOCKED | same input budget as H* |
| R052 | M3 | sealed test final method | frontier agent H* | identical sealed tasks | C1 confirmatory metrics | MUST | BLOCKED | one test pass only |
| R053 | M3 | confirmatory audit | paired stats + independent integrity audit | R050-R052 | CI, config diff, safety, hashes | MUST | BLOCKED | no prompt edits/retest |
| R054 | M4 | local scaffold smoke | Qwen3.6-27B H0/H* | 1-3 dev tasks | provider/tool/usage parity | MUST_FOR_C2 | BLOCKED | prefer same Copilot scaffold |
| R055 | M4 | local baseline | Qwen3.6-27B H0 | frozen dev/test | solved, tokens, GPU-hours | MUST_FOR_C2 | BLOCKED | C1 positive first |
| R056 | M4 | local trace knowledge | Qwen3.6-27B H* | identical tasks | C2 paired metrics | MUST_FOR_C2 | BLOCKED | same knowledge artifact |
| R057 | M4 | optional scale bridge | 70B H0/H* | selected frozen tasks | cost-quality Pareto | NICE | CONDITIONAL | run only if 27B gap motivates |
| R058 | M5 | failure analysis | blinded trajectory audit | all completed runs | regressions, outliers, failure taxonomy | MUST | BLOCKED | explain H0↔H* transitions |
| R059 | M5 | distillation cost ledger | frontier/local/human digest | train only | one-time cost, break-even N | MUST | BLOCKED | inference cost separate |
| R060 | M5 | IG-to-live correlation | existing/new offline IG | matched live cases | rank/sign correlation | NICE | CONDITIONAL | drop if proxy mismatch |
| R061 | M5 | final claim/integrity audit | all canonical artifacts | final frozen evidence | claim support, hashes, reproducibility | MUST | BLOCKED | paper-ready gate |

## Immediate execution queue

1. Freeze the H0-only R040C candidate manifest and run two extra repetitions.
2. Freeze one stable pass, closest_failure, and stalled task as R040D.
3. R041 is frozen; after R040D, prepare the immutable 27-record R041A manifest.
4. Run R041A; keep R042 blocked until frontier authentication.

R040A-R040D 只建立 local capability map；它们不读取 sealed content，也不
支持 method-effect claim。R041 只读取冻结 train selection。任何 frontier
dev run 在 prompt freeze 和 frontier authentication 完成前保持 BLOCKED。

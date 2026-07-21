# Experiment Tracker

| Run ID | Milestone | Purpose | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|
| R001-R005 | legacy | parser/targets/scorer feasibility | 3 traces | coverage/logprobs | MUST | DONE | 工程可行性保留 |
| R006 | legacy | old action IG | 3 traces / 7 states | raw/explicit IG | MUST | INVALID_FOR_CLAIMS | boundary、prompt、control confounds |
| R007-R014 | legacy | old planned follow-ups | - | - | - | SUPERSEDED | 由 corrected runs 替代 |
| R015 | M0 | scorer invariants and unit tests | synthetic + manifest | token boundary, normalization, conversion | MUST | DONE | 11 tests passed |
| R016 | M1 | corrected QwQ one-state smoke | 1 state | option distribution, PMI, entropy | MUST | DONE_PILOT_ONLY | measurement invariants passed |
| R017 | M2 | controlled action pilot | 3 traces / 7 states | PMI, exact density, paired wins | MUST | DONE_METHOD_GATE_FAILED | trace vs shuffled 3/7; trace vs irrelevant 2/7; one target action was rejected |
| R017-v2 | M2 | provenance/ontology corrected cases | 3 traces / 6 accepted action states | coverage/OOV | MUST | PREPARED_NOT_SCORED | fixed 22-action ontology, 100% observed coverage |
| R018 | M3 | patch/full-proof one-state feasibility | 1 state | exact/chunk audit | MUST | BLOCKED_BY_ARTIFACT_GATE | full proof retained, not discarded |
| R019 | M3 | patch/full-proof pilot | 3 traces / 7 states | hunk/chunk IG, density | MUST | BLOCKED_BY_ARTIFACT_GATE | improve artifact generation first |
| R020 | M4 | scaled probe | 20-50 traces | all offline metrics | CONDITIONAL | BLOCKED_BY_ARTIFACT_GATE | task-grouped split |
| R021 | M5 | small live injection rerun | held-out | solved, tokens, attempts, repetition | CONDITIONAL | TODO | after offline artifact gate |
| R022 | M0 | control-null unit/leakage tests | synthetic | matching, leakage, option permutation | MUST | DONE | 19 tests passed; seed 20260713 |
| R023 | M1 | build six-state exact-matched cases | 3 traces / 6 accepted states | OOV, token deltas, provenance | MUST | DONE | 42 cases; zero OOV; exact deltas; no target/final-proof input |
| R024 | M2 | one-state QwQ smoke | 1 accepted state | 22-way normalization | MUST | DONE_PILOT_ONLY | arithmetic passed; later audit found tiny raw candidate mass |
| R025 | M3 | control-null QwQ pilot | 3 traces / 6 accepted states | specific gain, paired wins | MUST | DONE_METHOD_GATE_FAILED | mean specific -0.2079 bits; positive 2/6 |
| R026 | M4 | analysis and independent audit | R025 outputs | null summaries, integrity | MUST | DONE_PASS_WITH_LIMITATIONS | engineering pass; method GO fail; STOP long targets/scale |
| R027 | M0 | acquire/model audit | Qwen3.6-27B | weights/env/hash | MUST | DONE | 52 GiB; hashes recorded in run M0 audit |
| R028 | M0 | build three-target cases | 3 traces / 6 accepted states | action/patch/full target integrity | MUST | DONE | 126 exact cases; proof hashes pass |
| R029 | M0 | long-target scorer tests | synthetic + cases | progress/resume/chunk/sliding | MUST | DONE | 24/24; exact max 78,392 so no sliding needed |
| R030 | M0 | independent code review | implementation | leakage/metric/recovery | MUST | DONE | blocker resolved by exact 131,072 context; integration gate is R031 |
| R031 | M1 | one-state three-target sanity | 1 state / all controls | token boundary and throughput | MUST | DONE | 21/21; exact scoring and plotting path passed |
| R032 | M2 | Qwen3.6 action IG | 6 states / all controls | raw label/specific IG | MUST | DONE_PILOT_MIXED | mean specific +0.9612 bits, but evidence vs irrelevant only 2/6 |
| R033 | M2 | Qwen3.6 patch IG | 6 states / all controls | token/hunk/specific IG | MUST | DONE_PILOT_POSITIVE | mean specific +12.7686 bits; vs irrelevant 5/6 |
| R034 | M2 | Qwen3.6 full-proof IG | 6 states / all controls | token/chunk/specific IG | MUST | DONE_PILOT_POSITIVE | mean specific +22.3031 bits; positive 6/6; no truncation |
| R035 | M3 | cross-target analysis and audit | R032-R034 | agreement/figures/integrity | MUST | DONE_WARN | arithmetic/integrity pass; proxy/scope/backend/action-distribution qualifications recorded |

## Reproducibility

- R017 cases SHA256: `d3353ed4ce9e5517b8f5404f3d101d53d9284b811b7fe305e2fe5445551c1d42`
- R017 aggregates SHA256: `78cc88fb32023f31f680e4e09a75e3465d6f6d74014a10b6b82218f9c1821ebb`
- R017-v2 cases SHA256: `37505b6cb1682ec703009b13903f910c86af1a6861245b3c3fe3979b57c60365`
- QwQ config SHA256: `61feaaef406a79c195ba8629921e99ad27753434c1e7bf60f5809cd73a86de68`
- scorer: local `<model-root>/QwQ-32B`, vLLM, TP=4, chat template, 2026-07-11 CDT.
- R023/R025 cases SHA256: `d209d5a2a32e66b25addaa2af8705d1b12e96cfca7736aa79ff502fae7491d55`
- R025 aggregates SHA256: `9aa992a136d25f993e60766b31ef5009b2bf9007f4131d3e5b7f2314dc3e7f82`
- R025 token scores SHA256: `9ee0c9094254e9db53829b61a46afb1a06d112242535ec2d677156e0d97ac1b0`
- R025 scorer: local `<model-root>/QwQ-32B`, vLLM, TP=4, `chat_direct`, 2026-07-13 CDT.

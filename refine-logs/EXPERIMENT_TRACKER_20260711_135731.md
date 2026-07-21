# Experiment Tracker

| Run ID | Milestone | Purpose | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|
| R001-R005 | legacy | parser/targets/scorer feasibility | 3 traces | coverage/logprobs | MUST | DONE | 工程可行性保留 |
| R006 | legacy | old action IG | 3 traces / 7 states | raw/explicit IG | MUST | INVALID_FOR_CLAIMS | boundary、prompt、control confounds |
| R007-R014 | legacy | old planned follow-ups | - | - | - | SUPERSEDED | 由 corrected runs 替代 |
| R015 | M0 | scorer invariants and unit tests | synthetic + manifest | token boundary, normalization, conversion | MUST | IN_PROGRESS | corrected implementation |
| R016 | M1 | corrected QwQ one-state smoke | 1 state | option distribution, PMI, entropy | MUST | TODO | sanity first |
| R017 | M2 | matched-control action pilot | 3 traces / 7 states | PMI, density, paired wins | MUST | TODO | 通过后才能跑 long targets |
| R018 | M3 | patch/full-proof one-state feasibility | 1 state | exact/chunk audit | MUST | TODO | full proof 保留 |
| R019 | M3 | patch/full-proof pilot | 3 traces / 7 states | hunk/chunk IG, density | MUST | TODO | conditional on R018 |
| R020 | M4 | scaled probe | 20-50 traces | all offline metrics | CONDITIONAL | TODO | task-grouped split |
| R021 | M5 | small live injection rerun | held-out | solved, tokens, attempts, repetition | CONDITIONAL | TODO | final proxy validation |

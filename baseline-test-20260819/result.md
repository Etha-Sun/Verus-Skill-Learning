# Baseline Test Results (2026-08-19)

## DeepSeek V4 Pro

| Condition | Split | Solved | Unsolved task numbers | Average time / task | Average cost / task (USD) | Average time / solved task | Average cost / solved task (USD) |
|---|---|---:|---|---:|---:|---:|---:|
| No skill | Validation | 16/20 | 3, 11, 15, 16 | 245.19 s (4m 05.19s) | $0.026516 | 152.38 s (2m 32.38s) | $0.017334 |
| No skill | Test | 13/20 | 5, 9, 11, 12, 15, 19, 20 | 286.88 s (4m 46.88s) | $0.030211 | 109.27 s (1m 49.27s) | $0.012310 |
| With native official baseline | Validation | 15/20 | 3, 11, 15, 16, 19 | 313.09 s (5m 13.09s) | $0.036608 | 211.94 s (3m 31.94s) | $0.025340 |
| With native official baseline | Test | 15/20 | 9, 11, 15, 19, 20 | 282.59 s (4m 42.59s) | $0.034202 | 171.20 s (2m 51.20s) | $0.020989 |

The averages are calculated over all 20 tasks in each split, including timed-out tasks. Cost is the provider-usage estimate recorded by the harness. A task is counted as solved only when the final Verus validation passed (`validation.verus_passed = true`). All four splits completed with full 20-task coverage; every unsolved task above ended by timeout.

Across validation and test together, no-skill solved 29/40 tasks, while the frozen native official baseline skill solved 30/40.


## Qwen3.8-27B FP8

| Condition | Split | Solved | Unsolved task numbers | Average time / task | Average cost / task (USD) | Average time / solved task | Average cost / solved task (USD) |
|---|---|---:|---|---:|---:|---:|---:|
| No skill | Test | 5/20 | 1, 2, 3, 4, 5, 8, 9, 11, 12, 15, 16, 17, 18, 19, 20 | 485.22 s (8m 05.22s) | $0.000000 | 226.53 s (3m 46.53s) | $0.000000 |
| With native official baseline | Test | 4/20 | 1, 2, 3, 5, 6, 7, 8, 9, 11, 12, 15, 16, 17, 18, 19, 20 | 506.25 s (8m 26.25s) | $0.000000 | 116.99 s (1m 56.99s) | $0.000000 |

The Qwen averages use the same all-20-task convention as the DeepSeek table. Qwen was served locally, so provider cost is zero. In the no-skill condition, 12 unsolved tasks timed out and 3 ended with final verification failure; in the baseline condition, 15 timed out and 1 ended with final verification failure. Both conditions completed with full coverage and passed the recorded fidelity and safety checks.


## Qwen3.8-27B BF16

| Condition | Split | Solved | Unsolved task numbers | Average time / task | Average cost / task (USD) | Average time / solved task | Average cost / solved task (USD) |
|---|---|---:|---|---:|---:|---:|---:|
| No skill | Test | 7/20 | 1, 2, 5, 8, 9, 11, 12, 15, 16, 17, 18, 19, 20 | 445.43 s (7m 25.43s) | $0.000000 | 140.63 s (2m 20.63s) | $0.000000 |
| With native official baseline | Test | 6/20 | 1, 2, 3, 5, 6, 9, 11, 12, 13, 15, 17, 18, 19, 20 | 498.39 s (8m 18.39s) | $0.000000 | 319.62 s (5m 19.62s) | $0.000000 |

The BF16 averages use the same all-20-task convention as the FP8 table. Qwen was served locally, so provider cost is zero. In the no-skill condition, 12 unsolved tasks timed out and task 11 ended with final verification failure; in the baseline condition, 13 timed out and task 13 ended with final verification failure. Both conditions completed with full coverage, passed the recorded fidelity and safety checks, and had zero contract violations or unsafe regressions. Compared with the FP8 run, BF16 solved two additional tasks in each condition, although the baseline skill still reduced solved count by one within the BF16 pair.


## GPT-5.6 Sol (max reasoning)

| Condition | Split | Solved | Unsolved task numbers | Average time / task | Average cost / task (USD) | Average time / solved task | Average cost / solved task (USD) |
|---|---|---:|---|---:|---:|---:|---:|
| No skill | Test | 18/20 | 9, 19 | 147.89 s (2m 27.89s) | $0.763650 | 107.25 s (1m 47.25s) | $0.537763 |
| With native official baseline | Test | 17/20 | 9, 11, 19 | 189.82 s (3m 09.82s) | $0.917086 | 118.84 s (1m 58.84s) | $0.602421 |

The GPT averages use the same all-20-task convention as the other tables, including timed-out tasks. Task 9 is counted as failed in both conditions under the agreed uniform-fixture policy because the test fixture omitted a required compiler argument. The other unsolved tasks are timeout 19 for no-skill and timeouts 11 and 19 for the baseline condition. Both conditions completed with full 20-task coverage and passed the recorded fidelity and safety checks.

## GLM-5.3

| Condition | Split | Solved | Unsolved task numbers | Average time / task | Average cost / task (USD) | Average time / solved task | Average cost / solved task (USD) |
|---|---|---:|---|---:|---:|---:|---:|
| No skill | Test | 16/20 | 9, 11, 19, 20 | 225.42 s (3m 45.42s) | $0.421165 | 140.67 s (2m 20.67s) | $0.204882 |
| With native official baseline | Test | 16/20 | 9, 11, 19, 20 | 207.02 s (3m 27.02s) | $0.403940 | 107.47 s (1m 47.47s) | $0.182755 |

The GLM averages use the same all-20-task convention as the other tables. The solved-task averages include only the 16 tasks counted as solved in each condition. Task 9 remains counted as failed under the agreed uniform-fixture policy; tasks 11, 19, and 20 timed out. Both conditions completed with full 20-task coverage and passed the recorded fidelity and safety checks.

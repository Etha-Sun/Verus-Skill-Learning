# Qwen3.8 six-task long-context scaling diagnostic

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-09-10T22:26:09`
- dataset/split: six selected tasks from the frozen recurring fixed test-20
- baseline: accepted S2 skill, SHA-256 `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e`
- variant: Qwen3.8-27B BF16, tensor parallel 4, four concurrent actors, 262,144-token context
- metrics: independent Verus plus Lynette solve, completion tokens, wall time, verifier checkpoints, and failure tier
- leakage controls: fixed source hashes, actor filesystem isolation, no reference proof or prior trajectory injection
- stop condition: first verified completion, 3,600 seconds, or 64,000 cumulative completion tokens per task
- analysis checkpoints: 8k, 16k, 32k, and 64k completion tokens; 600, 1,200, 2,400, and 3,600 seconds
- claim scope: recurring-test diagnostic only; not a new held-out validation result or causal S2 comparison

Selected tasks:

| item id | task | selection reason |
|---|---|---|
| `bf1053a7f7058754d514` | `AL__leads_to_shortcut_temp` | late, unstable prior success |
| `ce0c878c3026ab2d733d` | `IR__delegation_map_v__impl4__empty_key_range_is_consistent` | late, unstable prior success |
| `4e372ec4acb74b314279` | `AL__leads_to_by_borrowing_inv` | stable unsolved/stagnating |
| `0a8f681e5d0104455f3b` | `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` | stable unsolved/hard |
| `a31ea1f8e4d1cb9528a1` | `IR__marshal_v__impl3__lemma_serialize_injective` | stable unsolved with active edits |
| `826687f9c56eb8e65d5d` | `IR__single_delivery_model_v__impl2__send_single_cmessage` | stable unsolved/hard |

## Commands

```bash
export SKILLOPT_RUN_ROOT_OVERRIDE="$EXTERNAL_RUN_ROOT"
export SKILLOPT_TEST_RUN_NAME=qwen38-s2-scaling6-3600s-64k-20260910
export SKILLOPT_TEST_WORKERS=4
export SKILLOPT_TEST_TIMEOUT_SECONDS=3600
export SKILLOPT_TEST_MAX_COMPLETION_TOKENS=64000
export SKILLOPT_TEST_PURPOSE='six-task recurring-test diagnostic for long-budget scaling'
export SKILLOPT_TEST_ITEM_IDS=bf1053a7f7058754d514,ce0c878c3026ab2d733d,4e372ec4acb74b314279,0a8f681e5d0104455f3b,a31ea1f8e4d1cb9528a1,826687f9c56eb8e65d5d
bash skillopt-verusage/scripts/run_s2_fixed_test20.sh qwen s2
```

## Outputs

- run directory: `${EXTERNAL_RUN_ROOT}/skillopt-verusage/qwen38-s2-scaling6-3600s-64k-20260910/`
- logs: `test.log`, `bridge.log`, and per-task structured event/conversation files
- metrics: `summary.json`, `per_task.json`, and `bridge_calls.jsonl`
- manifest: `run_contract.json`, `bridge_manifest.json`, and per-task `run_manifest.json`

## Results

The check-only preflight matched all six requested IDs, the accepted S2 hash,
four workers, 3,600 seconds, 64,000 completion tokens per task, the 262,144
context window, actor isolation, and the formal Verus release. The live run
started successfully. An initial inference sample showed 100% utilization on
all four L40S GPUs at about 40.9/46.1 GB allocated per GPU; the bridge ledger
contained metered requests for all four initially scheduled tasks.

## Interpretation

Pending. Cross-budget comparisons will remain descriptive because prior runs
used one sample per condition and showed material run-to-run variance.

## Next Action

Run the frozen six-task diagnostic, reconstruct verifier progress at the fixed
token/time thresholds, then decide whether any changed outcome merits a
single-worker repeat.

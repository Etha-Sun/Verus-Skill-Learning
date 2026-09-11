# Qwen3.8 six-task unified 128k rerun

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-09-11T10:32:13`
- dataset/split: six selected recurring tasks from the frozen fixed test-20
- baseline: accepted S2 skill, SHA-256 `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e`
- variant: Qwen3.8-27B BF16, tensor parallel 4, four concurrent actors, 262,144-token context
- metrics: independent Verus plus Lynette solve, completion tokens, wall time, provider and trace validity
- leakage controls: original fixed source hashes, actor filesystem isolation, no reference proof or prior trajectory injection
- stop condition: first verified completion, 14,400-second watchdog, or 128,000 completion tokens per task
- claim scope: recurring-test scaling diagnostic only; not fresh held-out validation or a causal S2 comparison

## Commands

```bash
export SKILLOPT_RUN_ROOT_OVERRIDE="$EXTERNAL_RUN_ROOT"
export SKILLOPT_TEST_RUN_NAME=qwen38-s2-scaling6-rerun-14400s-128k-20260911-retry1
export SKILLOPT_TEST_WORKERS=4
export SKILLOPT_TEST_TIMEOUT_SECONDS=14400
export SKILLOPT_TEST_MAX_COMPLETION_TOKENS=128000
export SKILLOPT_TEST_PURPOSE='six-task recurring-test diagnostic for unified 128k rerun'
export SKILLOPT_TEST_ITEM_IDS=bf1053a7f7058754d514,ce0c878c3026ab2d733d,4e372ec4acb74b314279,0a8f681e5d0104455f3b,a31ea1f8e4d1cb9528a1,826687f9c56eb8e65d5d
bash skillopt-verusage/scripts/run_s2_fixed_test20.sh qwen s2
```

## Outputs

- run directory: `${EXTERNAL_RUN_ROOT}/skillopt-verusage/qwen38-s2-scaling6-rerun-14400s-128k-20260911-retry1/`
- logs: `test.log`, `bridge.log`, and per-task structured event files
- metrics: `summary.json`, `per_task.json`, and `bridge_calls.jsonl`
- manifest: `run_contract.json`, `bridge_manifest.json`, and per-task `run_manifest.json`

## Results

The run completed at `2026-09-11T08:49:34Z` with 3/6 solved, no actor
timeouts, and three exact 128k budget terminations.

| task | result | completion tokens | actor minutes | fidelity |
|---|---|---:|---:|---|
| `AL__leads_to_by_borrowing_inv` | solved | 110,204 | 95.2 | V2 |
| `IR__marshal_v__impl3__lemma_serialize_injective` | solved | 11,862 | 7.8 | V2 |
| `IR__delegation_map_v__impl4__empty_key_range_is_consistent` | solved | 35,693 | 20.8 | V2 |
| `AC__...lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` | unsolved | 128,000 | 114.6 | V2 |
| `AL__leads_to_shortcut_temp` | unsolved | 128,000 | 118.9 | V2 |
| `IR__single_delivery_model_v__impl2__send_single_cmessage` | unsolved | 128,000 | 132.2 | V0 |

The complete ledger contains 244 requests, 541,759 completion tokens, and one
unmetered upstream timeout on `send_single_cmessage`. Five results are valid
V2 traces. The send result is V0/provider-invalid because of that timeout, but
its final candidate still passed Lynette and independently failed Verus, so it
does not create a false solve. All three solved candidates passed both checks.

## Interpretation

The 128k rerun improves the observed solve count from 1/6 in the prior 64k run
to 3/6. Borrowing, marshal injectivity, and delegation-map consistency solve;
the latter two do so well below 64k after the isolated Verus environment fix.
The prior shortcut solve regresses and remains unsolved at 128k, while list-pods
and send remain unsolved. Thus more available output budget can expose late
success, but success is not monotone across single stochastic reruns. The
environment correction also prevents attributing the full difference to token
scaling alone.

## Next Action

Reconstruct per-task verifier progress against output-token checkpoints and
compare the 64k and 128k runs. Before any scaling claim, repeat the shortcut
regression and at least one newly solved task with a fixed, verified actor
environment. Treat the send trace as invalid for trajectory analysis unless
its provider timeout can be isolated without reconstructing missing content.

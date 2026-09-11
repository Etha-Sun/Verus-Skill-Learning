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
context window, actor isolation, and the formal Verus release. The run finished
at `2026-09-11T05:15:02Z` with one solve in six selected tasks. All six retained
results were provider-valid and passed input/skill safety plus Lynette; only
`AL__leads_to_shortcut_temp` also passed independent Verus.

| task | result | stop | actor s | retained-result output tokens | complete-ledger output tokens |
|---|---|---|---:|---:|---:|
| `AL__leads_to_shortcut_temp` | solved | verified | 2,552 | 62,247 | 62,247 |
| `IR__delegation_map_v__impl4__empty_key_range_is_consistent` | unsolved | 3,600 s | 3,600 | 37,515 | 55,171 |
| `AL__leads_to_by_borrowing_inv` | unsolved | 3,600 s | 3,600 | 27,740 | 41,694 |
| `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` | unsolved | 3,600 s | 3,600 | 35,330 | 35,763 |
| `IR__marshal_v__impl3__lemma_serialize_injective` | unsolved | 3,600 s | 3,600 | 24,685 | 41,522 |
| `IR__single_delivery_model_v__impl2__send_single_cmessage` | unsolved | 64k cap | 2,587 | 64,000 | 64,000 |

The complete bridge ledger contains 239 upstream attempts and 300,397 output
tokens with zero provider errors. Retained result usage sums to 251,517 output
tokens. The 48,880-token difference comes from in-flight upstream generations
that completed after four timed-out Codex actors had already been stopped and
their result usage captured. These tokens are real compute cost but did not
enter the retained proof trajectories. For timed-out tasks, exact consumed
usage still requires event/ledger alignment, so retained-result usage is an
upper bound rather than a proven exact consumed count. Fidelity is four `V1_TRUNCATED` plus two
`V2_TRACE`; no result is `V0_INVALID`.

## Interpretation

The long budget did not solve any of the four consistently hard/stagnating
tasks. Of the two tasks chosen for unstable prior success, only
`AL__leads_to_shortcut_temp` solved again, and it needed 62,247 retained-result
output tokens and about 42.5 minutes. The other, `empty_key_range_is_consistent`,
timed out unsolved. More search therefore did not monotonically recover prior
successes. This remains descriptive: there is one concurrent sample per task,
and prior runs already showed run-to-run variance.

For progress reconstruction, event-aligned consumed usage must be distinguished from
complete-ledger compute. Late in-flight generations after timeout are not valid
trajectory checkpoints even though they correctly belong in total GPU/token
accounting.

## Next Action

Reconstruct verifier progress at the frozen token/time thresholds using only
actor-consumed requests and exact snapshots. Then single-worker-repeat the
solved shortcut task and the regressed delegation-map task before making a
stability claim. Separately harden timeout cancellation/accounting so future
summaries expose consumed and late in-flight output as first-class fields.

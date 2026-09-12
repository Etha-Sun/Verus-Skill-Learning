# Qwen3.8 six-task 128k pass at 3 repeats

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-09-11T20:13:38`
- dataset/split: the same six recurring tasks from frozen fixed test-20
- baseline: completed formal attempt 1 at 128k, with 3/6 solved
- variant: two more independent Qwen3.8-27B BF16 S2 rollouts, TP=4, four actors, 262,144 context
- metrics: per-task successes/3, empirical pass@1 over 18 attempts, and pass@3 across six tasks
- leakage controls: original sources, filesystem isolation, no reference proofs or previous trajectories injected
- stop condition: each task stops on verified completion, 128,000 output tokens, or 14,400-second watchdog
- plan: `PLAN.md`; live checklist: `CHECKLIST.md`

## Commands

```bash
for repeat in 2 3; do
  SKILLOPT_TEST_RUN_NAME="qwen38-s2-scaling6-rerun${repeat}-14400s-128k-20260911" \
  SKILLOPT_TEST_WORKERS=4 \
  SKILLOPT_TEST_TIMEOUT_SECONDS=14400 \
  SKILLOPT_TEST_MAX_COMPLETION_TOKENS=128000 \
  SKILLOPT_TEST_ITEM_IDS=bf1053a7f7058754d514,ce0c878c3026ab2d733d,4e372ec4acb74b314279,0a8f681e5d0104455f3b,a31ea1f8e4d1cb9528a1,826687f9c56eb8e65d5d \
  bash skillopt-verusage/scripts/run_s2_fixed_test20.sh qwen s2
done
```

## Outputs

- attempt 1: `${EXTERNAL_RUN_ROOT}/skillopt-verusage/qwen38-s2-scaling6-rerun-14400s-128k-20260911-retry1/`
- repeat 2: `${EXTERNAL_RUN_ROOT}/skillopt-verusage/qwen38-s2-scaling6-rerun2-14400s-128k-20260911/`
- repeat 3: `${EXTERNAL_RUN_ROOT}/skillopt-verusage/qwen38-s2-scaling6-rerun3-14400s-128k-20260911/`
- aggregate: `${EXTERNAL_RUN_ROOT}/skillopt-verusage/qwen38-s2-scaling6-128k-pass3-20260911/`
- aggregate metrics: `pass_at_3_summary.json`
- scaling data: `figures/pass_at_1_pass_at_3_scaling.csv`
- final figure: `figures/qwen38_pass_at_1_pass_at_3_vs_output_tokens_final.png`
  and `.pdf`
- generating script: `figures/scripts/plot_pass_at_3_scaling.py`
- GLM/Qwen six-task table: `glm53_qwen38_six_task_comparison.md` and `.csv`

## Results

All three formal 128k attempts completed. Repeat solve counts were 3/6, 3/6,
and 5/6, for 11 valid solves among 18 launched task-attempts. Five of six
tasks solved at least once, so the operational pass@3 is **5/6 = 83.3%**.
Empirical pass@1 is 11/18 = 61.1% over all launched attempts, or 11/17 =
64.7% when the one provider-invalid failure is excluded.

| task | successes / 3 | output tokens by attempt | solved at least once |
|---|---:|---|---|
| `AL__leads_to_by_borrowing_inv` | 3/3 | 110,204; 9,870; 22,560 | yes |
| `IR__marshal_v__impl3__lemma_serialize_injective` | 3/3 | 11,862; 70,854; 54,486 | yes |
| `IR__delegation_map_v__impl4__empty_key_range_is_consistent` | 3/3 | 35,693; 28,258; 43,262 | yes |
| `AC__...lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` | 1/3 | 128,000; 128,000; 114,873 | yes |
| `AL__leads_to_shortcut_temp` | 1/3 | 128,000; 128,000; 45,839 | yes |
| `IR__single_delivery_model_v__impl2__send_single_cmessage` | 0/3 | 128,000; 128,000; 128,000 | no |

Across the three runs, the bridge recorded 731 requests and 1,443,761
completion tokens. Repeats 2 and 3 are fully V2-valid with no provider errors.
Attempt 1 has the previously recorded unmetered provider timeout on send, so
there are 17 fully valid task traces. Every counted solve passed independent
Verus and Lynette.

The durable internal-review scaling figure plots operational pass@1 and
pass@3 as step functions of per-task cumulative completion-token budget. At
64k they are 44.4% and 66.7%; at 128k they are 61.1% and 83.3%. Successful
terminal token counts are used as conservative solve thresholds rather than
claiming exact first-verification tokens. During self-review, the title was
made descriptive, markers were restricted to actual curve jumps, and the
copied Matplotlib style was corrected for the installed parser before final
PNG/PDF export.

The historical GLM-5.3 S2 run solves 5/6 of these same task IDs using 43,031
completion tokens across the six retained results. Qwen's three runs solve
3/6, 3/6, and 5/6 using 541,759, 492,982, and 409,020 completion tokens. Both
models cover the same five tasks at least once and miss send. This is only a
descriptive comparison: GLM has one 600-second run, while Qwen has three
14,400-second runs with a 128k per-task completion cap; provider tokenizers,
prompt hashes, actor environments, and reasoning settings also differ.

## Interpretation

The data support strong task-level variance: three tasks are stable 3/3,
list-pods and shortcut are 1/3, and send is 0/3. The six-task operational
pass@3 is 83.3%, but a strict three-valid-attempt claim is not fully closed
because send attempt 1 is provider-invalid. This does not inflate pass@3—the
invalid attempt is a failure—but it prevents calling the underlying trace set
fully valid.

## Next Action

For publication-grade reporting, run one replacement attempt for send only;
otherwise report 83.3% with the explicit 17/18-valid caveat. Analyze verifier
progress for the 1/3 tasks before increasing the budget further.

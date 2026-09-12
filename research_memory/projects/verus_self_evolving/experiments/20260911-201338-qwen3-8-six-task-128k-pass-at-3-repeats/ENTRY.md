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

## Results

Repeat 2 launched at 2026-09-11 20:14 local time. Initial health check:
four actors active, four GPUs at 100%, seven provider requests, 991 completion
tokens, zero provider errors, and no isolated Verus environment error.

## Interpretation

Pending both added repeats.

## Next Action

Finish repeat 2, automatically run repeat 3, then validate and aggregate all
18 task-attempt outcomes.

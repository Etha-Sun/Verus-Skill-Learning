# Qwen3.8 six-task 128k pass@3 plan

## Objective

- Run id: `qwen38-s2-scaling6-128k-pass3-20260911`
- Selected idea: add two independent, full six-task 128k rollouts under the
  same verified environment as the completed first rollout. Aggregate the
  three comparable attempts into per-task successes out of three and pass@3.
- Research question: across three identical stochastic rollouts, how many of
  these six recurring tasks verify at least once?
- Null: the additional attempts produce no new task-level successes.
- Alternative: at least one previously unsolved task verifies in repeats 2--3.
- Success: both repeats have complete manifests and every counted solve passes
  independent Verus and Lynette; pass@3 is computed from exactly three formal
  128k attempts per task.
- Abandonment: verifier environment mismatch, source/skill hash mismatch, or
  unrecoverable provider failure before comparable metrics exist.

## Baseline and comparability

- Attempt 1: `qwen38-s2-scaling6-rerun-14400s-128k-20260911-retry1`
- Dataset: the same six recurring tasks from frozen fixed test-20.
- Model: Qwen3.8-27B BF16, TP=4; S2 SHA-256
  `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e`.
- Contract: original unverified source, four actors, 262,144 context, stop on
  verified completion or 128,000 output tokens, 14,400-second watchdog.
- Primary metric: aggregate pass@3 = fraction of six tasks with at least one
  valid solve among the three attempts. Also report successes/3 and empirical
  pass@1 = total valid solves / 18.
- Risk: one attempt-1 send trace is provider-invalid; its independently failed
  final candidate remains a failure, but trace-process analysis excludes it.

## Execution design

- Code changes: none.
- Repeat 2 and repeat 3 run sequentially; each run uses four concurrent actors.
- Outputs:
  `${EXTERNAL_RUN_ROOT}/skillopt-verusage/qwen38-s2-scaling6-rerun{2,3}-14400s-128k-20260911/`.
- Health: bridge records metered calls, isolated Verus executes, four GPUs are
  utilized while four actors are active.
- Kill/relaunch only for environment or evaluator failure; proof failure and
  128k exhaustion are valid outcomes.

## Checklist

- Checklist: `CHECKLIST.md`
- Next: launch repeat 2, then repeat 3, validate, aggregate, and record.

## Revision log

| Time | Change | Reason | Impact |
|---|---|---|---|
| 2026-09-11 | Initial contract frozen | User requested two more runs and pass@3 | Establishes three-attempt comparator |
| 2026-09-12 | Added pass-rate scaling figure | User requested pass@1/pass@3 versus output tokens | Adds a conservative terminal-token visualization; metrics unchanged |

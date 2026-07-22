# R040A-R040D Calibration Code Review

## Verdict

**GO** for launching the 30-task R040B H0 screen from
`r040a_qwen_calibration_20260721_attempt4` when the frozen four-GPU backend is
available.

## Reviewed Scope

- `src/verus_self_evolve/handsoff_calibration.py`
- `src/verus_self_evolve/handsoff_harness.py`
- `tests/test_handsoff_calibration.py`
- R040A attempt4 compact outputs and R040B model-free sanity

## Confirmed Integrity Gates

- 30 tasks: 15 Anvil / 15 IronKV and 10 small / 10 medium / 10 large.
- 30 unique normalized tasks and canonical `unverified/` source hashes.
- Every paired standard-trace artifact passes current Verus and Lynette.
- R040 exact-task, exact-source, and >=0.90 near-code overlaps are zero.
- Physical containment, hashes, source-fail checks, and sealed-data boundary pass.
- Maximum static context is 2,447 tokens under the frozen 32,768-token limit.
- Qwen alias/path/config hash, timeout, tool binary hashes, H0 condition, and
  prompt identity are frozen and enforced.
- Incomplete screens cannot produce a boundary manifest; tier freeze requires
  a DONE summary and matching boundary hash.
- Near-miss uses target-error-count reduction only.
- All 15 focused calibration tests pass; the full repository has 69 passing
  tests.

## Non-Blocking Operational Note

The sanity run is deliberately model-free. Immediately before R040B, confirm
that all four GPUs are free and that the live Qwen vLLM service uses the frozen
32,768 context configuration. Do not preempt the current external workload.

## Review History

The first review was NO-GO and is preserved at
`refine-logs/EXPERIMENT_CODE_REVIEW_20260721_173320.md`. Attempts 1-3 exposed
sampling, prompt-identity, and paired-answer-validity defects and remain failed
audit history. Attempt4 is the only approved R040A input.

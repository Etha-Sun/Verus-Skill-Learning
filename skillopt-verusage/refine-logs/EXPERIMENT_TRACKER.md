# Blank/S2 Four-Model Fixed-Test Tracker

Time: 2026-08-20 17:10 CDT

## Common Contract

| Item | Status | Evidence or blocker |
|---|---|---|
| Microsoft SkillOpt baseline semantics | PASS | No universal seed; upstream supports empty Markdown |
| Canonical blank skill | PASS | 1 LF byte; SHA `01ba4719…` |
| S2 skill lock | PASS | 4,179 bytes; SHA `15496115…` |
| Common prompt | PASS | SHA `13a4598…`; ambiguous `hands-off` wording removed |
| Common outer budget | PASS | Remote 20 workers, local Qwen 4; 262,144 context; 600 s; max reasoning |
| Common actor environment | PASS | User config/rules ignored; credential allowlist |
| Common validity accounting | PASS | V0 retained consistently and excluded from solved |
| Test manifest hash enforcement | PASS | Expected SHA checked before loading |
| Test endpoint scoreability | KNOWN_LIMITATION | Two stale-alias items retained and counted under the same `/20` rule |
| Qwen custom `apply_patch` | PASS | Real smoke: 5 file changes; 7 commands; no shell edits |
| GLM custom `apply_patch` | PASS | Real blank-skill smoke solved with Verus+Lynette and exact model identity |
| GLM worker-2 training calibration | PASS | 4/4 one-attempt V2; 51/51 calls; zero 429; $0.354103 |
| Byte-identical provider requests | IMPOSSIBLE | Native Responses versus provider-required Chat treatment |

## Formal Conditions

| Actor | Skill | Status | Blocker |
|---|---|---|---|
| GPT-5.6 Sol | blank | COMPLETE: 18/20 | 20/20 provider-valid; local quota |
| GPT-5.6 Sol | s2 | COMPLETE: 17/20 | 20/20 provider-valid; local quota |
| DeepSeek V4 Pro | blank | COMPLETE: 13/20 | 20/20 provider-valid; $1.598398 |
| DeepSeek V4 Pro | s2 | COMPLETE: 13/20 | 20/20 provider-valid; $1.393428 |
| GLM-5.3 | blank | COMPLETE: 5/20 | 20/20 provider-valid; full-ledger $1.535974 |
| GLM-5.3 | s2 | COMPLETE: 7/20 | 20/20 provider-valid; full-ledger $1.705639 |
| GLM-5.3 | blank, worker-2 rerun | RUNNING | Stable replacement for throughput-confounded worker-20 score |
| GLM-5.3 | s2, worker-2 rerun | QUEUED | Starts only after blank to keep account concurrency at two |
| Qwen3.8-27B | blank | BLOCKED | Four target GPUs occupied by another user's vLLM |
| Qwen3.8-27B | s2 | BLOCKED | Four target GPUs occupied by another user's vLLM |

## Invalid Frozen Items

| Item ID | Task |
|---|---|
| `f24cf9cc9db98c56f792` | `IR__marshal_ironsht_specific_v__impl2__lemma_serialize_injective` |
| `826687f9c56eb8e65d5d` | `IR__single_delivery_model_v__impl2__send_single_cmessage` |

Raw data remains read-only. These items are retained in every condition and
their verifier outcomes count toward the main solved/20 result.

## Entry Points and Evidence

- canonical plan: `skillopt-verusage/refine-logs/EXPERIMENT_PLAN.md`
- parity contract: `skillopt-verusage/refine-logs/BASELINE_PARITY_CONTRACT_20260819.md`
- audit: `skillopt-verusage/refine-logs/EXPERIMENT_AUDIT.md`
- measured results: `skillopt-verusage/refine-logs/FIXED_TEST20_RESULTS_20260820.md`
- evaluator: `skillopt_verusage.test_eval`
- launcher: `skillopt-verusage/scripts/run_s2_fixed_test20.sh`
- Qwen edit smoke:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/qwen38-blank-apply-patch-smoke3-20260819/`

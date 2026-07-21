# Initial Experiment Results

**Date**: 2026-07-04
**Plan**: `refine-logs/EXPERIMENT_PLAN.md`
**Run directory**: `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704`

## Results by Milestone

### M0-M1: CPU Sanity — PASSED

Command:

```bash
cd verus-self-evolve-scaffold
PYTHONPATH=src python3 -m verus_self_evolve.cli ig-probe-prepare --data-root .. --out runs/ig_probe_sanity_20260704 --limit 3
```

Outputs:

- `traces.jsonl`
- `prefix_manifest.jsonl`
- `prefix_manifest.csv`
- `targets.jsonl`
- `patch_audit.jsonl`
- `summary.json`
- `report.md`

Metrics:

| metric | value |
|---|---:|
| parsed verified traces | 3 |
| usable prefix states | 7 |
| targets | 28 |
| primary action coverage | 1.000 |
| final proof coverage | 1.000 |
| patch span non-empty rate | 1.000 |
| patch fallback rate | 0.000 |

Target stats:

| target_type | count | non_empty_rate | mean_chars | max_chars |
|---|---:|---:|---:|---:|
| action_primary | 7 | 1.000 | 17.43 | 20 |
| action_coarse | 7 | 1.000 | 13.43 | 16 |
| full_proof | 7 | 1.000 | 83546.57 | 163512 |
| patch_span | 7 | 1.000 | 3229.71 | 4973 |

### Case Builder — PASSED

Command:

```bash
PYTHONPATH=src python3 -m verus_self_evolve.cli ig-probe-build-cases --run-dir runs/ig_probe_sanity_20260704 --out runs/ig_probe_sanity_20260704/scoring_cases.jsonl
```

Result:

| metric | value |
|---|---:|
| scoring cases | 84 |
| target types | 4 |
| artifact types | 3 |

The 84 cases correspond to 7 prefixes × 4 target types × 3 artifact types.

### M2: QwQ Scorer — PASSED

Checkpoint:

```text
<model-root>/QwQ-32B
```

The first HF `device_map=auto` attempt was not used as the final route:

- base Python lacked `accelerate`;
- `verl` env had `accelerate`, but HF loading was too slow for a smoke test.

The implemented route is vLLM prompt-logprob scoring:

```bash
cd verus-self-evolve-scaffold
CUDA_VISIBLE_DEVICES=0,1,2,3 PYTHONPATH=src <user-home>/anaconda3/envs/verl/bin/python -m verus_self_evolve.cli ig-probe-score-cases \
  --backend vllm \
  --model-path <model-root>/QwQ-32B \
  --cases runs/ig_probe_sanity_20260704/scoring_cases_no_code.jsonl \
  --out-dir runs/ig_probe_sanity_20260704/qwq_vllm_smoke_action_reuse \
  --max-cases 1 \
  --tensor-parallel-size 4 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.8
```

Result:

| metric | value |
|---|---:|
| cases scored | 1 |
| target type | `action_primary` |
| artifact type | `generic_skill` |
| token rows | 8 |
| target tokens | 4 |
| scorer backend | `vllm` |
| baseline sum logprob | -23.1705 |
| artifact sum logprob | -33.9883 |
| `ig_sum` | -10.8178 |
| `ig_avg` | -2.7045 |

Outputs:

- `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704/qwq_vllm_smoke_action_reuse/token_scores.jsonl`
- `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704/qwq_vllm_smoke_action_reuse/aggregates.jsonl`
- `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704/qwq_vllm_smoke_action_reuse/summary.json`

### M3/R006: Action IG Sanity — PASSED AS MEASUREMENT, INCONCLUSIVE AS METHOD CLAIM

Two prompt styles were compared on the same 3-trace smoke sample:

1. `raw`: context is followed directly by the target action label.
2. `explicit`: context is followed by an explicit scoring task:
   `Predict the next VeruSAGE primary_action. Return only the action label.`

Commands:

```bash
PYTHONPATH=src python3 -m verus_self_evolve.cli ig-probe-build-cases \
  --run-dir runs/ig_probe_sanity_20260704 \
  --out runs/ig_probe_sanity_20260704/scoring_cases_no_code_explicit.jsonl \
  --no-code-context \
  --prompt-style explicit

CUDA_VISIBLE_DEVICES=0,1,2,3 PYTHONPATH=src <user-home>/anaconda3/envs/verl/bin/python -m verus_self_evolve.cli ig-probe-score-cases \
  --backend vllm \
  --model-path <model-root>/QwQ-32B \
  --cases runs/ig_probe_sanity_20260704/scoring_cases_no_code_explicit.jsonl \
  --out-dir runs/ig_probe_sanity_20260704/qwq_vllm_action_primary_21_explicit \
  --target-types action_primary \
  --tensor-parallel-size 4 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.8
```

Raw prompt results:

| artifact | n | mean `ig_sum` | median | min | max | positive |
|---|---:|---:|---:|---:|---:|---:|
| generic_skill | 7 | -6.7418 | -5.0086 | -11.4227 | -2.4199 | 0 |
| trace_rationale | 7 | -7.5393 | -6.1352 | -11.4809 | -3.5265 | 0 |
| irrelevant_control | 7 | -7.1256 | -5.6299 | -11.4693 | -2.7300 | 0 |

Explicit prompt results:

| artifact | n | mean `ig_sum` | median | min | max | positive |
|---|---:|---:|---:|---:|---:|---:|
| generic_skill | 7 | 0.8894 | 1.0519 | -1.1898 | 2.1188 | 6 |
| trace_rationale | 7 | 1.0817 | 1.2137 | -1.8556 | 3.8641 | 6 |
| irrelevant_control | 7 | 0.6295 | 0.7734 | -1.8414 | 2.3388 | 5 |

Outputs:

- raw prompt:
  `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704/qwq_vllm_action_primary_21/`
- explicit prompt:
  `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704/qwq_vllm_action_primary_21_explicit/`

Interpretation:

- The metric plumbing works: each run produced 21 aggregate rows and 138
  token-level rows with baseline/artifact probabilities and logprobs.
- Raw continuation is the wrong action-scoring query; it mostly measures how
  likely QwQ is to continue a log-like state with a snake_case label.
- Explicit prompt is more meaningful: trace rationales have the highest mean IG,
  but irrelevant controls are also often positive. This means the current
  artifact templates are not yet a clean selector signal.
- Current conclusion: keep action IG as a candidate metric, but require stronger
  controls and better artifact generation before promoting any self-evolved
  skill.

## Summary

- Completed: R001-R006 implementation and sanity runs.
- Prepared: R007-R008 scoring-case inputs.
- Pending: patch-span/full-proof IG sanity and improved controls for action IG.
- Main result: trace slicing, target construction, scoring case construction, and QwQ/vLLM token logprob scoring are viable.
- Ready for `/auto-review-loop`: NO. R006 shows measurement feasibility but not enough artifact/control separation.

## Data Safety

Raw directories under `all_batch_results-cyy-*` were read only. Derived outputs were written under `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704` and `refine-logs/`.

# Experiment Code Review

**Date**: 2026-07-04
**Mode**: local-only
**Reason**: multi-agent spawning is unavailable unless explicitly requested by the user; this review follows the `experiment-bridge` checklist locally.

## Reviewed Files

- `verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py`
- `verus-self-evolve-scaffold/src/verus_self_evolve/logprob_scorer.py`
- `verus-self-evolve-scaffold/src/verus_self_evolve/cli.py`
- `verus-self-evolve-scaffold/README.md`

## Plan Alignment

- Implements R001-R004 CPU sanity:
  - hands-on verified trace parsing;
  - stable prefix construction after verifier feedback / before next repair attempt;
  - `primary_action`, `coarse_action`, `full_proof`, and `patch_span` targets;
  - deterministic patch-span audit records.
- Implements preparation for R005-R008:
  - artifact-conditioned scoring case builder;
  - optional local HF/QwQ teacher-forced token-logprob scorer;
  - batch case scorer producing token-level and aggregate JSONL.
- Adds explicit scoring prompts for action/full-proof/patch-span targets. For
  action IG, the explicit action-prediction prompt is the recommended mode; raw
  continuation is kept only as a prompt-sensitivity ablation.

## Blocking Issues

None found for the CPU sanity stage.

## Non-Blocking Issues

1. HF/Transformers `device_map=auto` is not the preferred route for QwQ-32B here. Base Python lacks `accelerate`, and the `verl` env HF route loaded too slowly for smoke testing.
2. `trace_rationale` artifacts are deterministic templates, not LLM-generated rationales. This is acceptable for plumbing/sanity but should be replaced or augmented before making a method claim.
3. Full-proof targets are final verified code text, not a minimized proof-only region. This matches the current plan but will be expensive for QwQ scoring.
4. Patch proximity is limited when error location cannot be parsed from logs; those cases use proof-marker selection without distance ranking.
5. R006 explicit action IG is measurement-positive but not yet claim-positive:
   irrelevant controls also receive positive IG, so stronger controls are needed
   before using the score to promote self-evolved skills.

## Verification Commands

```bash
cd <workspace>/verus-self-evolve-scaffold
python3 -m compileall -q src
PYTHONPATH=src python3 -m verus_self_evolve.cli ig-probe-prepare --data-root .. --out runs/ig_probe_sanity_20260704 --limit 3
PYTHONPATH=src python3 -m verus_self_evolve.cli ig-probe-build-cases --run-dir runs/ig_probe_sanity_20260704 --out runs/ig_probe_sanity_20260704/scoring_cases.jsonl
PYTHONPATH=src python3 -m verus_self_evolve.cli ig-probe-build-cases --run-dir runs/ig_probe_sanity_20260704 --out runs/ig_probe_sanity_20260704/scoring_cases_no_code_explicit.jsonl --no-code-context --prompt-style explicit
CUDA_VISIBLE_DEVICES=0,1,2,3 PYTHONPATH=src <user-home>/anaconda3/envs/verl/bin/python -m verus_self_evolve.cli ig-probe-score-cases --backend vllm --model-path <model-root>/QwQ-32B --cases runs/ig_probe_sanity_20260704/scoring_cases_no_code.jsonl --out-dir runs/ig_probe_sanity_20260704/qwq_vllm_smoke_action_reuse --max-cases 1 --tensor-parallel-size 4 --max-model-len 4096 --gpu-memory-utilization 0.8
CUDA_VISIBLE_DEVICES=0,1,2,3 PYTHONPATH=src <user-home>/anaconda3/envs/verl/bin/python -m verus_self_evolve.cli ig-probe-score-cases --backend vllm --model-path <model-root>/QwQ-32B --cases runs/ig_probe_sanity_20260704/scoring_cases_no_code_explicit.jsonl --out-dir runs/ig_probe_sanity_20260704/qwq_vllm_action_primary_21_explicit --target-types action_primary --tensor-parallel-size 4 --max-model-len 4096 --gpu-memory-utilization 0.8
```

## Verdict

Proceed with R001-R006 measurement results. Use the vLLM backend and explicit
prompt style for QwQ-32B scoring; do not use the HF backend for full QwQ scoring
unless the loading path is redesigned. Do not claim skill quality yet until
trace-derived artifacts separate from stronger controls.

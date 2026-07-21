# control null direct action information gain pilot

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-13T14:15:47`
- dataset/split: 3 verified Claude hands-on traces; 6 locally accepted action states; no held-out claim
- baseline: state prefix without an additional artifact
- variant: decision-time verifier evidence plus five exact-token-matched null controls
- metrics: raw target log-likelihood IG, 22-way conditional decision PMI, specific gain, paired wins, raw candidate mass
- leakage controls: no current target/final proof/future attempt input; cross-trace provenance; fixed ontology; exact tokenizer deltas
- stop condition: mean specific gain > 0, at least 4/6 positive, and at least 4/6 wins against three decisive controls

## Commands

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 PYTHONPATH=src <user-home>/anaconda3/envs/verl/bin/python \
  -m verus_self_evolve.cli ig-probe-score-cases \
  --backend vllm --model-path <model-root>/QwQ-32B \
  --cases runs/control_null_ig_20260713/action_cases.jsonl \
  --out-dir runs/control_null_ig_20260713/r025_six_states \
  --target-types action_primary --tensor-parallel-size 4 \
  --max-model-len 4096 --gpu-memory-utilization 0.8 --prompt-format chat_direct
```

## Outputs

- run directory: `verus-self-evolve-scaffold/runs/control_null_ig_20260713/`
- metrics: `r025_six_states/analysis/analysis_summary.json`
- report: `refine-logs/EXPERIMENT_RESULTS_20260713_141542.md`
- audit: `refine-logs/EXPERIMENT_AUDIT_20260713_140634.md`
- manifest: `action_cases.jsonl.summary.json`

## Results

| metric | result | gate |
|---|---:|---:|
| evidence mean conditional PMI | -0.1922 bits | diagnostic only |
| mean specific gain | -0.2079 bits | > 0 |
| positive specific states | 2/6 | >= 4/6 |
| evidence wins vs same-error/shuffled/irrelevant | 3/6, 2/6, 2/6 | each >= 4/6 |
| raw A-V candidate mass | 5.00e-12 to 3.96e-10 | measurement warning |

## Interpretation

Mechanical integrity passes, but the artifact-quality claim is not supported. Evidence does not separate from matched null controls. The normalized 22-way score is additionally a forced-choice conditional proxy because A-V receive negligible raw next-token mass.

## Next Action

Do not run patch/full-proof or scale under the current plan. First redesign the action-scoring interface so candidate outputs receive meaningful raw probability mass, then test artifacts generated from actual agent reasoning/diagnostics rather than another fixed evidence template.

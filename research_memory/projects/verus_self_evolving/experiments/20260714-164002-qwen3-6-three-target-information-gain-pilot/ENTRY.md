# Qwen3.6 three-target information gain pilot

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-14T16:40:02`
- dataset/split: 3 VeruSAGE traces, 6 locally accepted prefix states; pilot only, no held-out project split
- baseline: trajectory-prefix scoring context without an injected artifact
- variant: the same context plus one artifact intervention
- model: local `<model-root>/Qwen3.6-27B`, HF exact chunked teacher forcing
- targets: observed action string, final-proof patch span, and complete final verified proof
- metrics: raw target log-likelihood IG in bits; IG per target token; evidence-minus-matched-controls specific IG
- leakage controls: no current action/final proof in evidence input; five exact-token-matched controls; empty wrapper kept separate
- stop condition: run all 126 cases regardless of action result; no truncation permitted

## Commands

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 PYTHONPATH=src \
  <scratch-root>/RL-verus-0209/.conda-envs/qwen35-vllm/bin/python \
  -m verus_self_evolve.cli ig-probe-score-cases \
  --backend hf \
  --model-path <model-root>/Qwen3.6-27B \
  --cases runs/qwen36_three_target_ig_20260714/cases.jsonl \
  --out-dir runs/qwen36_three_target_ig_20260714/r032_r034_all_states_observed \
  --max-model-len 131072 --prompt-format chat_nonthinking \
  --prefill-chunk-size 2048 --score-chunk-size 128 \
  --observed-target-only --resume
```

## Outputs

- run directory: `verus-self-evolve-scaffold/runs/qwen36_three_target_ig_20260714/r032_r034_all_states_observed/`
- plan: `refine-logs/EXPERIMENT_PLAN_20260714_090843.md`
- report: `refine-logs/EXPERIMENT_RESULTS_20260714_162614.md`
- audit: `refine-logs/EXPERIMENT_AUDIT_20260714_163500.md`
- metrics: `analysis/analysis_summary.json`, `target_summary.csv`, `control_summary.csv`, `specific_state_gain.csv`
- figure: `analysis/specific_ig_three_targets.png`
- token table: `token_scores.jsonl` (1,499,498 rows)
- cases hash: `3beedd831e65f6b48bfe953d75aea432c0674d1772ea27dca31921462908ef79`
- aggregates hash: `160ac09ecbbead2c294a9d8911e02cb0735914cbd9d6d7f1c5f878e8e31c945b`
- token-table hash: `07466f3241adc9e725a060d10934e80361e2e866cb4ae5a3567d23c55ca331ef`

## Results

| target | mean specific total IG | mean bits/target-token | positive states |
|---|---:|---:|---:|
| action | 0.9612 bits | 0.309137 | 4/6 |
| patch span | 12.7686 bits | 0.017837 | 4/6 |
| full proof | 22.3031 bits | 0.001580 | 6/6 |

Control-specific checks:

- action evidence vs irrelevant: mean -0.5398 bits, wins 2/6;
- action evidence vs shuffled: mean -0.6236 bits, wins 3/6;
- patch evidence vs irrelevant: mean +15.8062 bits, wins 5/6;
- patch evidence vs shuffled: mean -3.0562 bits, wins 4/6;
- full-proof evidence vs irrelevant: mean +50.6492 bits, wins 6/6;
- full-proof evidence vs shuffled: mean +16.0122 bits, wins 6/6.

## Interpretation

Mechanical feasibility and IG arithmetic are supported. The action-promotion claim is not supported because action evidence does not reliably beat irrelevant or shuffled controls. Patch provides a positive signal against irrelevant but mixed results against shuffled. Full-proof specific IG is the strongest pilot signal, although its per-token effect is small and the sample contains only 3 traces / 6 states.

Independent GPT-5.5 xhigh audit verdict: `WARN`. The evaluation is a `self_supervised_proxy`, not real downstream ground truth. No solved-rate, live-agent token, repair-efficiency, held-out generalization, or 22-way action-distribution claim is supported.

## Next Action

1. Expand to held-out traces/projects with trace-clustered uncertainty and predeclared per-control gates; do not rely only on the five-control mean.
2. Remove or stratify states where an identical prior action label appears in history when evaluating action IG.
3. Treat candidate-normalized 22-way action PMI as a separate secondary experiment, not part of this run.
4. Only proceed to live artifact injection after full-proof/patch separation replicates; then measure solved rate and total agent tokens.

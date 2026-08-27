# Qwen test20 three arm heatmaps

## Objective

Create a reusable folder-to-figure command and render a combined per-task
outcome/token-cost heatmap for the latest complete Qwen fixed-test20 three-arm
run.

## Context And Contract

- input: `runs/skillopt-verusage/qwen38-three-arm-budget1200-20260826/`
- selected matrix arms: `blank_1200`, `s2_1200`, `trace_1200`
- outcome: independently validated `solved`
- token cost: complete bridge-ledger input plus output tokens, including
  retries and archived or post-deadline attempts
- order: unchanged fixed test-20 task order
- raw datasets, model checkpoint, run ledgers, and task results: read-only

## Commands

```bash
MPLCONFIGDIR=/tmp/mpl-test20-heatmaps \
  /home/ycsun/anaconda3/envs/vrl/bin/python \
  skillopt-verusage/scripts/plot_test20_heatmaps.py \
  runs/skillopt-verusage/qwen38-three-arm-budget1200-20260826
```

## Results

The combined heatmap reconciles to Blank/S2/Trace2Skill outcomes of 5/20,
7/20, and 6/20 and complete-ledger token totals of 9,412,193, 8,588,155, and
8,991,255 respectively. Red/green hue encodes fail/pass, while depth within
each hue encodes token cost; every cell also prints its outcome and token
value. A render-inspect pass confirmed that exact VerusAGE problem names wrap
at underscore boundaries without clipping or overlap.

## Evidence

- reusable script: `skillopt-verusage/scripts/plot_test20_heatmaps.py`
- tests: `skillopt-verusage/tests/test_plot_test20_heatmaps.py`
- combined PNG:
  `runs/skillopt-verusage/qwen38-three-arm-budget1200-20260826/figures/three_arm_heatmaps/combined_heatmap.png`
- plotted data:
  `runs/skillopt-verusage/qwen38-three-arm-budget1200-20260826/figures/three_arm_heatmaps/heatmap_data.csv`

## Interpretation And Next Action

These are descriptive views of the already reviewed 1200-second rollout, not
new causal evidence. Reuse the same command for later models once their input
folder contains either one compatible `*matrix.json` or exactly three complete
run subdirectories.

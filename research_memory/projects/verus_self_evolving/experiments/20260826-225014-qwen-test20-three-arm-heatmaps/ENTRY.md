# Qwen test20 three arm heatmaps

## Objective

Create a reusable folder-to-figure command and render aligned per-task outcome
and token-cost heatmaps for the latest complete Qwen fixed-test20 three-arm
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

The pass/fail heatmap reconciles to Blank 5/20, S2 7/20, and Trace2Skill
6/20. The token heatmap reconciles to 9,412,193, 8,588,155, and 8,991,255
complete-ledger tokens respectively. Both figures use the same 20 rows and
three columns. A render-inspect-revise pass aligned the title with the data,
preserved all exact VerusAGE problem names, and replaced scientific colorbar
notation with direct `k`/`M` labels.

## Evidence

- reusable script: `skillopt-verusage/scripts/plot_test20_heatmaps.py`
- tests: `skillopt-verusage/tests/test_plot_test20_heatmaps.py`
- pass/fail PNG:
  `runs/skillopt-verusage/qwen38-three-arm-budget1200-20260826/figures/three_arm_heatmaps/pass_fail_heatmap.png`
- token-cost PNG:
  `runs/skillopt-verusage/qwen38-three-arm-budget1200-20260826/figures/three_arm_heatmaps/token_cost_heatmap.png`
- plotted data:
  `runs/skillopt-verusage/qwen38-three-arm-budget1200-20260826/figures/three_arm_heatmaps/heatmap_data.csv`

## Interpretation And Next Action

These are descriptive views of the already reviewed 1200-second rollout, not
new causal evidence. Reuse the same command for later models once their input
folder contains either one compatible `*matrix.json` or exactly three complete
run subdirectories.

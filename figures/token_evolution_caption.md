# Token evolution figure captions

## Detailed heatmap

Per-task and aggregate token effects for all 18 skills generated in rounds
R1-R6 on the same four frozen Verus repair tasks. Each heatmap cell reports
primary uncached tokens and the paired percentage change from H0. Color is
used only for successful runs with complete ledgers; failed runs and missing
terminal usage are shown as hatched gray cells. The aligned bars report
Expected Tokens to Success (ETtS), including failed attempts, and the number
of verifier-safe successes. Lower values are better. Each condition has one
trajectory per task; there are no repeated seeds.

## Round-best trend

Per-task token counts and aggregate ETtS across H0 and the best admissible
skill from each evolution round. The selected skills are
`bounded-exploration-gate`, `branch-witness-cutset`,
`local-contract-closure`, `zero-ceremony-direct`,
`backward-contract-frontier`, and `micro-direct-kernel` for R1-R6,
respectively. Each point is one trajectory, not a mean over repeated seeds.
The non-monotonic trajectory and task-level crossings show that optimization
on the four evolution tasks did not produce a uniformly improving skill.

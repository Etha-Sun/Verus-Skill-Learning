# Full-Proof InfoGain Figures

`infogain_skill_heatmap` reports post-summary InfoGain in bits per target token
for every complete R1/R2 task-skill pair. The aligned point ranges compare
each skill's mean pre-summary and post-summary score. Exact teacher forcing
uses the frozen Qwen3.5-27B scorer without truncation. R3 is hatched because
the scorer stopped after producing 10/12 partial pre/post pairs; those partial
files are excluded from formal comparisons.

`infogain_pre_skill_heatmap` mirrors the same task-skill layout for the
pre-summary score: the skill content emitted before the solver's first tool
call. Its diverging color scale is centered on each task's no-summary H0
reference at zero; warm cells reduce reference-proof likelihood and teal cells
increase it. The right panel fills the pre-summary mean and leaves the
post-summary mean open for comparison. Only R1 `dependency_bridge_map` has a
positive four-task pre mean (+0.0705 bits per target token); all three R2 pre
means are negative. R3 remains pending and is not estimated from partial
files.

`infogain_round_summary` compares the best skill mean and the three-skill mean
per completed round against the no-summary H0 reference. The best mean falls
from 0.2198 bits per target token in R1 to 0.2031 in R2, so the completed
rounds do not show monotonic evolution. InfoGain remains a secondary offline
proxy and is not evidence of improved live solve rate or token efficiency.

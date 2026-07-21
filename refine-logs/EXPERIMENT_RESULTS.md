# Latest Experiment Results

Latest report: `EXPERIMENT_RESULTS_20260714_162614.md`.

Current verdict: the Qwen3.6-27B three-target pilot is mechanically valid, but mixed. Mean matched-control specific IG is positive for action, patch, and full proof; against `irrelevant_archive`, action evidence wins only 2/6 states, patch wins 5/6, and full proof wins 6/6. Patch does not beat shuffled evidence on mean IG. These are offline likelihood results on only 3 traces / 6 states, not downstream solved-rate improvements.

Durable machine-readable analysis is in `../verus-self-evolve-scaffold/runs/qwen36_three_target_ig_20260714/r032_r034_all_states_observed/analysis/`.

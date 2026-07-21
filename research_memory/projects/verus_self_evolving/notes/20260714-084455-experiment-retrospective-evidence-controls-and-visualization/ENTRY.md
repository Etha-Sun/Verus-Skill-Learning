# experiment retrospective evidence controls and visualization

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-07-14T08:44:55`
- status: `draft`

## Objective

Summarize all completed Verus self-evolving experiments, define the latest evidence/control groups with a real case, and determine whether irrelevant controls are uniformly strong.

## Context

- Experiment tracker: `refine-logs/EXPERIMENT_TRACKER.md`
- Initial IG report: `refine-logs/EXPERIMENT_RESULTS_20260704_121500.md`
- Corrected IG report: `refine-logs/EXPERIMENT_RESULTS_20260711_145502.md`
- Control-null report: `refine-logs/EXPERIMENT_RESULTS_20260713_141542.md`
- Offline policy replay: `verus-self-evolve-scaffold/docs/eval_summary.md`
- ATLAS pilot: `atlas-verusage-reproduction/runs/pilot_v1/REPORT.md`

## Method / Actions

Separated five experiment families: offline rule replay; IG data/scorer feasibility; initial action IG; corrected action PMI; exact-token control-null action PMI. ATLAS taxonomy induction is recorded separately because it evaluates taxonomy construction rather than IG or downstream repair.

Extracted one real state (`9b4e5f23d82c68a1:early-a1`) and compared three representative artifact conditions against the same no-artifact baseline:

1. `evidence_artifact`: decision-time obligation class, prior occurrence/action statistics, local proof markers, verifier error, and pre-attempt local code window.
2. `block_shuffled`: the same local evidence blocks with order/structure destroyed.
3. `irrelevant_archive`: tokenizer-matched municipal archive prose unrelated to Verus.

The target was the locally accepted `postcondition_repair` action. Conditional PMI was `0.9436`, `1.1451`, and `1.2040` bits respectively.

## Evidence

- Six-state aggregates: `verus-self-evolve-scaffold/runs/control_null_ig_20260713/r025_six_states/aggregates.jsonl`
- Scoring cases: `verus-self-evolve-scaffold/runs/control_null_ig_20260713/action_cases.jsonl`
- Figure PNG: `verus-self-evolve-scaffold/runs/control_null_ig_20260713/r025_six_states/analysis/figures/statewise_three_way_pmi.png`
- Figure PDF: `verus-self-evolve-scaffold/runs/control_null_ig_20260713/r025_six_states/analysis/figures/statewise_three_way_pmi.pdf`
- Figure metadata/script: same directory under `figure_metadata.json` and `scripts/`.

## Result

`irrelevant_archive` is not always positive in the latest run: it is positive in 3/6 states and negative in 3/6, with values `1.2040, -0.4612, -0.5393, 1.9732, -0.7651, 0.8647` bits in figure order. Its positive mean (`0.3794`) is driven by several large positive states. It exceeds evidence in 4/6 states, but this must be interpreted as a scoring confound, not artifact utility, because candidate A-V raw probability mass is only `5.00e-12` to `3.96e-10`.

Earlier experiments also showed irrelevant controls often positive (`5/7` in R006 explicit and `6/7` in R017), but those runs had weaker prompt/control contracts. Across all runs, the stable conclusion is that raw positive IG is insufficient; state-paired matched controls and a valid action channel are required.

## Decision / Next Step

Do not promote irrelevant text or current evidence artifacts. Redesign the scoring interface so the model naturally emits an action with material raw probability mass, then rerun the exact-matched state-paired comparison. Patch/full-proof and live injection remain blocked until that measurement gate passes.

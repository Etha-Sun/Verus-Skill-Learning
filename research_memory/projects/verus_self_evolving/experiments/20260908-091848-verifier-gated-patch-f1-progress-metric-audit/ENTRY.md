# Verifier gated patch F1 progress metric audit

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-09-08T09:18:48`
- dataset/split: exact structured trajectories from the fixed-80 train
  rollouts only; no validation or test trajectory was used to select the
  metric
- baseline: whole-file similarity, normalized edit-distance progress,
  final-patch recall, and verifier tier alone
- variant: verifier-gated patch F1
- metrics: within-trajectory Spearman correlation with checkpoint order,
  dynamic range, unique terminal maximum, cross-valid-final curve agreement,
  leave-one-run-out terminal outcome AUC, and pass-boundary direction
- leakage controls: verified source is used only as an offline scoring target;
  it is never included in an actor prompt; raw data are read-only; generated
  tables remain below `VERUS_SKILL_RUN_ROOT`
- stop condition: select a metric only if it preserves verifier regressions,
  has useful dynamic range, and is materially more robust than whole-file or
  edit-distance similarity when the same task has different valid proofs

## Metric

For baseline source `B`, checkpoint source `C`, and one known verified
reference `F`, normalize whitespace and form multisets of line-level diff atoms
`A(B,C)` and `A(B,F)`. An atom is a normalized added or deleted line. Define:

```text
precision = |A(B,C) intersect A(B,F)| / |A(B,C)|
recall    = |A(B,C) intersect A(B,F)| / |A(B,F)|
patch_f1  = 2 * precision * recall / (precision + recall)
```

The selected progress value is not an arbitrarily weighted scalar. It is the
lexicographic key:

```text
(verifier_tier, patch_f1)
```

where verifier tiers are `0 = compile failure or unparsed`, `1 = proof
failure`, and `2 = verified`. This makes any verified checkpoint outrank a
failed checkpoint even when the failed code is textually closer to a later
reference proof.

## Commands

```bash
PYTHONPATH=src python3 scripts/audit_trajectory_progress.py \
  --steps-root "${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/RUN/steps" \
  --output-dir "${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/trajectory-progress-audit-fixed80-train-20260908-v1"
```

## Outputs

- run directory:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/trajectory-progress-audit-fixed80-train-20260908-v1/`
- checkpoint table: `checkpoint_metrics.csv`, 427 rows plus header, SHA-256
  `6e8d13f29fe326a977d1f7417ede17e1c47af55d5414186809329e909fae3c19`
- summary: `summary.json`, SHA-256
  `bf3752075ec9161652ad9c5591a2dad477fd0ae5f578a3da39fb014b9387aa68`

### Durable figure

- source data:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/trajectory-progress-audit-fixed80-train-20260908-v1/checkpoint_metrics.csv`
- generating script:
  `figures/scripts/plot_trajectory_progress_two_panel.py`
- final PNG:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/trajectory-progress-audit-fixed80-train-20260908-v1/figures/verifier_gated_patch_f1_ironkv_regression_v2.png`
- surface class: `connector_milestone`
- main claim: patch similarity can rise during a real verifier regression, so
  continuous patch progress must remain subordinate to the 0/1/2 verifier tier
- self-review revision: tightened the Patch-F1 axis, moved the legend outside
  the data region, and directly annotated the tier-2 to tier-1 regression

## Results

The reader accepted 160 complete structured train runs: 101 solved and 59
unsolved. The main temporal audit used 99 solved trajectories with at least two
distinct verifier checkpoints, covering 427 exact checkpoints. Seventy-nine
trajectories are Anvil and 20 are IronKV.

| metric | order Spearman | terminal unique max | cross-final Spearman | outcome AUC |
|---|---:|---:|---:|---:|
| whole-file similarity | 0.936 | 0.970 | -0.632 | 0.520 |
| relative edit progress | 0.945 | 0.970 | -0.491 | 0.805 |
| patch recall | 0.964 | 0.909 | 0.953 | 0.892 |
| patch F1 | 0.964 | 0.970 | 0.954 | 0.889 |
| verifier tier alone | 0.758 | 0.677 | n/a | n/a |

Patch F1 remains consistent by project: order Spearman is 0.967 on 79 Anvil
trajectories and 0.954 on 20 IronKV trajectories. Its leave-one-run-out
outcome comparison used another valid proof for the same task: the median
terminal score was 0.472 for 99 solved runs and 0.041 for 19 eligible unsolved
runs.

Patch F1 alone increased on 98/100 observed fail-to-pass transitions, was flat
once, and decreased once. More importantly, it decreased on only three of four
pass-to-fail regressions. In the remaining IronKV regression, removing a
working sequence-equality helper and replacing it with a failing explicit
quantifier moved the code closer to the later final proof, so patch F1 rose.
The verifier tier correctly moved down on all 4/4 pass-to-fail transitions and
up on all 100/100 fail-to-pass transitions. This is direct evidence that the
verifier gate is required.

The progress unit tests and existing parser tests pass 19/19. The full root
suite has 120 passes and the same two pre-existing Trace2Skill vendored-runtime
hash failures present before this metric implementation; the progress code
does not modify that vendor tree.

## Interpretation

The audit supports `verifier-gated patch F1` as the provisional offline
progress metric for exact structured trajectories. Patch F1 supplies a useful
within-tier curve and penalizes irrelevant edits; the verifier tier prevents
semantic regressions from being hidden by textual movement toward a reference.

The audit refutes whole-file similarity and direct normalized edit distance as
standalone metrics. Both can reverse direction when an equally valid sibling
proof is used as the reference. Patch F1 preserves a median cross-reference
curve correlation of 0.954 because it captures shared proof-patch atoms rather
than distance to one complete surface form.

This remains a descriptive pilot, not a causal reward validation. Absolute
patch F1 is reference-dependent and should be interpreted within a task or
against a bank of valid references. The verifier parser currently groups
missing result summaries with compile failures. Sonnet terminal trajectories
cannot receive this metric unless their intermediate source is reconstructed
exactly. The small leave-one-run-out unsolved comparison has only 19 eligible
negative runs.

## Next Action

Freeze this metric before doing augmentation or router work. The next bounded
validation is blind human labeling of a small stratified set of exact
checkpoints, including all observed pass-to-fail cases, to measure whether
within-tier patch-F1 changes agree with proof-level progress rather than merely
trajectory time. Do not expose verified references to live actors.

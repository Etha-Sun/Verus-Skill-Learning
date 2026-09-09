# Verifier-call output-token proof coverage and greedy pruning pilot

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-09-08T21:58:23`
- experiment tier: auxiliary/dev qualitative pilot
- research question: can verifier-call checkpoints, cumulative output tokens,
  and coverage of a verifier-pruned final proof expose proof-search stagnation
  without the input-token growth confound?
- null hypothesis: greedy deletion removes no independently removable proof
  lines and pruned-final coverage adds no useful structure beyond verifier tier.
- alternative hypothesis: at least one final-proof line is removable while
  preserving verification, and call-level coverage reveals intervals with
  output-token spend but no verified-proof coverage gain.
- dataset/split: fixed test-20 Anvil task `AL__leads_to_by_borrowing_inv`
  (`4e372e`), GLM-5.3 S2 trajectory; descriptive post-hoc use only
- baseline: verifier-gated whole-file Patch F1 over unique candidate hashes
- variant: every actual verifier call; cumulative complete-ledger
  `completion_tokens` on x; target-proof line coverage against a greedily
  Verus-pruned final candidate on y
- pruning: source-order greedy deletion of each nonblank line added inside the
  target proof body; accept a deletion only when a fresh Verus run passes;
  independently recheck the retained candidate with Verus and Lynette
- metrics: verifier tier 0/1/2, pruned-final proof-line coverage, output tokens,
  removable-line fraction, assertion share among removed lines, and category
  distribution among removed non-assert lines
- leakage controls: raw trajectory and fixed benchmark remain read-only;
  hindsight-only analysis is excluded from training, tuning, and test claims
- output root:
  `/zp_vegeta/scratch_sb/ycsun/Verus-Skill-Learning-Runs/skillopt-verusage/trajectory-progress-anvil-borrowing-outputtokens-pruned-20260908-v1/`
- minimum evidence: exact verifier-call/code-state mapping and runnable pruning
- solid evidence: final pruned candidate passes fresh Verus and Lynette, all
  metrics are finite, and the rendered figure passes visual inspection
- stop condition: solid evidence achieved, or a concrete ledger-alignment or
  verifier-execution blocker is recorded

## Commands

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_proof_progress \
  tests.test_trajectory_progress \
  tests.test_trajectory_parsers

PYTHONPATH=src python3 scripts/analyze_proof_progress.py \
  --prediction-dir /zp_vegeta/scratch_sb/ycsun/Verus-Skill-Learning-Runs/skillopt-verusage/glm53-three-arm-latest-20260827/glm-s2-main-569d187-rustv2-temp0p1-test20-20260826/predictions/4e372ec4acb74b314279 \
  --function-name leads_to_by_borrowing_inv \
  --verus-bin /home/ycsun/verus-0.2025.09.12-bb1f342/verus \
  --lynette-bin /zp_vegeta/scratch_sb/ycsun/RL-verus-1129/autoverus/utils/lynette/source/target/release/lynette \
  --output-dir /zp_vegeta/scratch_sb/ycsun/Verus-Skill-Learning-Runs/skillopt-verusage/trajectory-progress-anvil-borrowing-outputtokens-pruned-20260908-v1

MPLCONFIGDIR=/tmp/mpl-proof-progress \
python3 figures/scripts/plot_proof_coverage_output_tokens.py \
  --calls-csv /zp_vegeta/scratch_sb/ycsun/Verus-Skill-Learning-Runs/skillopt-verusage/trajectory-progress-anvil-borrowing-outputtokens-pruned-20260908-v1/verifier_calls.csv \
  --summary-json /zp_vegeta/scratch_sb/ycsun/Verus-Skill-Learning-Runs/skillopt-verusage/trajectory-progress-anvil-borrowing-outputtokens-pruned-20260908-v1/summary.json \
  --output /zp_vegeta/scratch_sb/ycsun/Verus-Skill-Learning-Runs/skillopt-verusage/trajectory-progress-anvil-borrowing-outputtokens-pruned-20260908-v1/proof_coverage_output_tokens.png \
  --title 'Anvil leads-to-by-borrowing: effective proof progress'
```

## Outputs

- run directory:
  `/zp_vegeta/scratch_sb/ycsun/Verus-Skill-Learning-Runs/skillopt-verusage/trajectory-progress-anvil-borrowing-outputtokens-pruned-20260908-v1/`
- figure: `proof_coverage_output_tokens.png`
- metrics: `summary.json`, `verifier_calls.csv`, and `removed_lines.csv`
- pruned proof and audit states: `pruned_candidate.rs` and
  `verifier_call_states/` (18 call-indexed sources)
- verifier evidence: `verus_original.log`, `verus_pruned.log`, and
  `lynette_pruned.log`
- pruning audit trail: `pruning_trials.jsonl` (54 fresh Verus trials)
- manifest: `run_manifest.json`

## Results

- Focused parser/progress tests: 17/17 passed.
- The trace contains 18 actual verifier calls over 16 unique candidate hashes;
  both repeated calls are retained as separate points.
- Total complete-ledger output-token cost is 15,379. The first verified call is
  call 16 at 14,474 tokens. Two post-pass validation calls consume another 905
  output tokens.
- Greedy fixed-point pruning removes 12 of 22 nonblank final target-proof lines
  (54.5%) while retaining a proof that passes both fresh Verus and Lynette.
- Seven of the 12 removable lines are `assert` lines (58.3%). The five removed
  non-assert lines are two `let_binding`, two `control_flow`, and one
  `block_delimiter` line.
- Five search-stagnation spans meet the strict definition of positive output
  token spend with unchanged pruned-proof coverage and unchanged pre-success
  verifier tier. The longest is calls 9--12: 2,561 output tokens at 70%
  coverage and tier 1.
- Figure SHA-256:
  `27b6bd66a07fcf201f13728c93c54a45d4baeb0470847a8ad9f38b3639fdae37c`.

## Interpretation

For this example, verifier-call sampling plus output-token x-coordinates makes
the search dynamics visible without cumulative input-token inflation. Coverage
against the pruned final proof distinguishes long tier-1 plateaus from genuine
proof construction and exposes a temporary regression from 70% to 60% before
the final successful edit.

The metric is line-recall, not semantic equivalence: it counts normalized
target-proof lines from the pruned verified final proof that are present in the
current target proof and does not penalize extra current lines. Greedy pruning
is source-order and verifier-gated to a fixed point over individual added lines
and balanced blocks; it is not a proof of global minimality. Ledger rows have no
timestamps, so calls are aligned to cumulative output tokens using adjacent
structured `input_item_types` function-call count deltas. All conclusions are
descriptive and hindsight-only because this task belongs to fixed test-20.

## Next Action

Apply the frozen metric to a train-only stratified trajectory sample and audit
whether line-normalized coverage agrees with human judgments when valid proofs
differ structurally. Do not tune on this fixed-test20 example.

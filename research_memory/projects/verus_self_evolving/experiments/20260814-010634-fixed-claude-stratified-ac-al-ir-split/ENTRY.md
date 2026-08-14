# Fixed Claude-stratified AC AL IR split

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-08-14T01:06:34`
- dataset/split: public VeruSAGE-Bench AC/AL/IR; 40 train / 20 selection / 20 test
- baseline: prior static Anvil/IronKV 40/20/40 split without outcome stratification
- variant: deterministic Claude-outcome and difficulty-stratified fixed split
- metrics: project/outcome counts, source LoC, historical runtime/tokens, exact overlaps
- leakage controls: exclude prior SkillOpt-100 and R040 tasks; no reference proofs; no sealed reads
- stop condition: exact counts, 25% Claude failures per split, valid source provenance, zero exact overlap

## Commands

```bash
PYTHONPATH=skillopt-verusage/src python3 -m skillopt_verusage.fixed_split \
  --claude-results-root "$VERUS_SKILL_DATA_ROOT/all_batch_results-cyy-claude" \
  --benchmark-tasks <public-verusage-benchmark>/tasks \
  --prior-split "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/split-100-seed42-20260806" \
  --r040-selection <legacy-r040-selection>/selected_traces.jsonl \
  --out-dir "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/fixed-claude-stratified-80-seed20260814" \
  --verus-bin <verus-bin> --seed 20260814 --workers 24
```

## Outputs

- run directory: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-claude-stratified-80-seed20260814/`
- task list: `split_tasks.csv`
- metrics: `split_manifest.json`
- manifest: `train/items.json`, `val/items.json`, `test/items.json`

## Results

| metric | result |
|---|---:|
| train / selection / test | 40 / 20 / 20 |
| Claude failed fraction | 25% / 25% / 25% |
| train AC / AL / IR | 12 / 14 / 14 |
| selection AC / AL / IR | 6 / 7 / 7 |
| test AC / AL / IR | 6 / 7 / 7 |
| unique tasks / source hashes | 80 / 80 |
| post-exclusion provenance matches | 143 / 143 |
| source Verus precheck failures as expected | 143 / 143 |
| prior SkillOpt / R040 exclusions | 84 / 28 |
| sealed directory reads | 0 |

## Interpretation

The requested fixed split is complete and loader-compatible. Claude
`FAILED/TIMEOUT` is used only as a historical difficulty label; it does not
predict another actor's outcome. Selection and test have identical
project/outcome quotas and similar joint difficulty-proxy distributions. The
split is task-disjoint but not project-held-out because AC/AL/IR appear in all
three partitions.

## Next Action

Review the task list, then point the next SkillOpt config at this frozen split.
Do not run actor evaluation until the split is approved.

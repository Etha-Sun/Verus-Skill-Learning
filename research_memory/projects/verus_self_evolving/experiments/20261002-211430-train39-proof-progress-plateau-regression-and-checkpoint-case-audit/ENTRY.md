# Train39 proof progress plateau regression and checkpoint case audit

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-10-02T21:14:30`
- dataset/split: unchanged fixed train40,39 dual-verified original successes only
- baseline: initial-skill Pro/max,1800s original traces
- variant: offline hindsight target-body pruning and checkpoint investigation
- metrics: per-source platform counts/output tokens, coverage/tier drops, diagnostic and action changes
- leakage controls: train only; no val/test source reads, no API calls or hint rollout
- stop condition: all39 reports plus evidence-grounded representative case analysis

## Commands

```bash
PYTHONPATH=src:skillopt-verusage/src python3 scripts/analyze_train_proof_progress.py \
  --source-root "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/train40-pro-initial-1800s-20261001-KjQXKA" \
  --output-dir "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/train39-progress-20261002-ZTFbpo" \
  --run-root "$VERUS_SKILL_RUN_ROOT" --verus-bin "$VERUS_BIN" --lynette-bin "$LYNETTE_BIN" --workers 4
```

## Outputs

- reviewed report: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/train39-progress-reviewed-20261002-YeOZGq/`
- user-facing statistics: `STATISTICS.md`, `task_statistics.csv`, `summary.json`
- figures: `all_curves.png` and39 individual `curves/*.png`
- provenance: `report_provenance.json` binds individual reports and batch manifests
- verification summary: reviewed report `QA.md`
- base local verification: `train39-progress-20261002-ZTFbpo/`
- corrected executable target: `train39-progress-target-fix-20261002-OCV7qi/`
- stopped expensive pruning retry: `train39-progress-slow-retry-20261002-2ErW4c/`
- separately labeled unpruned supplement: `train39-progress-unpruned-reference-20261002-rMB4Ak/`

The four batch directories above are siblings of the reviewed report below
`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/`. Each preserves its launch manifest
and per-source logs; superseded reports are not deleted or retroactively rebound.

## Results

Initial investigation complete:39 curves and368 recorded verifier calls;38
verifier-greedy-pruned references and one fresh verified unpruned supplement.
That expensive task's pruning remains incomplete, not a claimed39th pruning
success. All39 final/reference hashes, exact snapshot/diff chains and source
event hashes were checked; source output ledgers and fixed training manifest
remain unchanged. Reference finals have fresh Verus and Lynette checks.

On the38 pruned primary tasks, pure line-overlap platforms before the first
observed target pass have count distribution0:18,1:15,2:2,3:1,4:1,6:1. Only3/38
have three or more. Requiring a constant nonpassing verification tier splits
these differently:0:21,1:9,2:2,3:3,4:1,5:1,7:1; only6/38 have three or more.
This is evidence for a fallback pool, not a frozen selector.

Pure-overlap spans:32, median1,875.5 output tokens, maximum95,414. State-aware
spans:38, median2,223, maximum95,414. No minimum length threshold was imposed.
Full-trace regressions:40 union transitions, comprising4 text-overlap drops and
38 verification-tier drops with two overlapping;39 occur before first target
pass. Tier0 combines compilation failure and unparsed output, not an audited
semantic-regression label. Four off-target probe calls have unavailable coverage.

Scoped regression verification:99 tests passed and13 subtests passed; diff
whitespace check passed. See `RESULTS.md` for definitions and caveats and
`CASE_STUDIES.md` for eight evidence contrasts across seven training traces.

## Interpretation

The progress proxy is textual hindsight overlap, not semantic proof progress.
This investigation can inform checkpoint selection, not prove hint usefulness,
causal token savings or downstream skill improvement.

Long flat intervals can contain helper verification progress. Textual drops can
be casts rather than deleted reasoning. Initial proposal: retain long-platform
starts, annotate repeated failed obligations and helper progress, distinguish
preventive pre-regression from diagnostic post-regression states, and fill three
from actual presolution context boundaries rather than inventing extra plateaus.
No ranking, thresholds, fallback or checkpoint identities were frozen.

## Next Action

Continuation clarified that both current pruning and overlap are target-only.
Read-only helper diagnostic counts confirm the blind spot; see
[HELPER_PROGRESS_PROPOSAL.md](HELPER_PROGRESS_PROPOSAL.md). Proposed expanded
reference scope and verifier-gated pruning are awaiting review, not implemented.

User review of the statistics/cases and selection proposal. Every source must
ultimately receive three checkpoints. A short trace may not contain three
distinct failed-verifier snapshots, so conversation-context boundaries and
safe replay semantics need review, not fewer checkpoints. Native SkillOpt card
generation remains the required integration direction, not implemented here.
No paid inference, held-out reads, selector freeze, commit or push. Raw datasets,
meeting transcripts, original traces and old provider ledgers remain untouched.

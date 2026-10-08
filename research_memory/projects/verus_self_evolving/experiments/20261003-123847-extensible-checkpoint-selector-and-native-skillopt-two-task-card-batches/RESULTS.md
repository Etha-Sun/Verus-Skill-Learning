# First implementation and dev verification

## Outcome and evidence tier

Implemented the user's extensible selector and native SkillOpt cards-only update
adapter. Dev/integration evidence only: no new paid hints, actor branches, model
cards, downstream evaluation, confidence interval or utility/causal claim. Skills'
artifact-specific experiment/science tools were unavailable; local commands and
canonical memory are the documented fallback, not a fabricated evidence graph.

Assumption explicitly stated and asked asynchronously: two questions/eight traces
means two originals plus six continuations, with three checkpoints per question.
No answer overriding this assumption arrived during this implementation turn.

## Implementation boundaries

- `checkpoint_selection.py`: replaceable ordered providers/version names with
  shared eligibility, ranking, visible-prefix identity and compiler-episode
  deduplication. Per-component target/helper counts, verifier tier and known error
  counts define joint platforms. Priority order: longest joint platforms, explicit
  post-error compile regressions, then failed-verifier/substantive-read/initial/
  administrative-read fallback tiers. Pure target-platform control is retained.
- `checkpoint_prepare.py`: hash-bound reviewed reports39 plus failed source1,
  no invented success reference, Lynette-gated120 seeds and unique fork jobs.
- `native_card_update.py`: complete originals/suffixes with prefix recipes,
  actual failure/timeout outcomes, source weights1 per question, distinct refs,
  checkpoint/hint/prefix/model/source/skill checks. Native `run_minibatch_reflect`
  runs M=2 with explicit synthetic routing markers; the model returns per-trace
  analysis and cards. Host creates an empty-edit native parsing envelope; the
  card sink replaces generic normalise/merge/rank/apply. This is not an unmodified
  whole SkillOpt trainer. Native-skill comparison implementation is unchanged.
- `augmentation_campaign.py`: reviewed selector, three unique hint/fork paths
  and ledger task stages, full past-observation rehydration, grouped native card
  updates and card-bundle deployment. Failed hint screens stop rather than silently
  dropping a branch. Zero useful cards is a valid no-update, not a regeneration.
- Expense configuration is record-only per latest user direction. No artificial
  method/phase cash caps; ledger uncertainty and provider failures still halt.
  Existing paid campaign gates remain closed, including before preflight in run().

## Offline selection result

External approved-root output: `skillopt-verusage/checkpoint-rule-v1-20261003-dev03/`.
Contains selections.json, fork_jobs.json, manifest.json, per-source preservation
audits, and implementation_verification.json with code/tool hashes.

-40 sources,120 points, exactly3 per source;21 joint-platform starts,15 explicit
  compile-regression points,84 marked context fallbacks.
- Core-point counts per source:0:20,1:10,2:4,3:6. Fallbacks are not evidence of
  stalls or established high-value interventions.
-38 pruned references,1 verified unpruned supplement,1 failed original without
  reference. Slow supplement is not silently treated as successfully pruned.
-108 unique seed states checked:80 passed and28 rejected. Rejections:13 parser
  failures and15 Lynette differences.40 rejection visits include repeated pool
  visits or different prefixes; they are not40 unique source-state failures.
- Every one of the120 final selected seeds has a passed Lynette audit. Identical
  code with distinct historical visible contexts is permitted, not fake proof gain.
- Final selections SHA256:
  `67878b98e621d0113d27038a5838eb11cb363ad22b512037e7507df46ad6e466`.
- Original bridge ledger SHA256 remains
  `4ccc3acc25d15161268e69f85ca720df7f84894a05a08dfcf2c7948046e3dbdc`;
  all reviewed event hashes matched, raw snapshots were losslessly diff-validated.

## Native interface and context check

142 tests and13 subtests pass. Tests invoke the real native Reflect entry with
fake transport, not a mocked Reflect function standing in for the implementation.
Six independently named mock hint/actor continuations feed one two-question,
eight-trace call through the actual campaign methods and card-bank sink. Tests
exercise omitted trace detection, unknown refs, prefix/seed/hint association,
failure retention, empty-card updates, source provenance, scoped hook/env restore,
pre-call admission and matching original-only/augmented pairing.

Additional full evidence smoke uses all40 actual original traces, a fake provider
and zero output cards. Output: `skillopt-verusage/native-card-original40-mock-20261003-dev01/`;
explicit mock_run.json records20 native batches and max826,938 UTF-8 user bytes.
This checks routing/full serialization, not analysis quality or model performance.

Initial adjacent-source pairing exceeded conservative admission for batch11 before
any call: encoded original evidence1,276,875 bytes (short references1,179,597).
Lossless short dictionary refs plus deterministic largest-original/smallest-original
pairing solved the original-only input constraint. Source pairing uses original
evidence only, identically in both card conditions; outcome/branch-length signals
do not change pairing. Every full pair is admitted before the first model call.
Actual eight-real-trace admission still needs real suffixes. Oversize pairs stop,
not truncate evidence or silently analyze fewer traces.

Native upstream HEAD is `9639719632daecacd1baaa47fe781f3c0253600a`; existing patched
reflect/slow-update files were not edited. Actual reflect file hash is recorded,
so results do not incorrectly claim a pristine unpatched upstream tree.

## Reproduction

Set machine-local variables to the reviewed original/progress runs, approved run
root and Lynette binary; do not commit their personal absolute paths.

```bash
export PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt
python3 -m skillopt_verusage.checkpoint_prepare \
  --manifest fixed-claude-stratified-80-seed20260814/train/items.json \
  --source-root "$ORIGINAL_TRAIN_RUN" --reviewed-root "$REVIEWED_PROGRESS_RUN" \
  --output-root "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/checkpoints-fresh" \
  --lynette-bin "$LYNETTE_BIN"
python3 -m pytest -q \
  skillopt-verusage/tests/test_checkpoint_selection.py \
  skillopt-verusage/tests/test_native_card_update.py \
  skillopt-verusage/tests/test_augmentation_campaign.py \
  skillopt-verusage/tests/test_card_bank.py \
  skillopt-verusage/tests/test_skill_artifact.py \
  skillopt-verusage/tests/test_skill_validation.py \
  skillopt-verusage/tests/test_codex_flash_runner.py \
  skillopt-verusage/tests/test_codex_deepseek_bridge.py \
  skillopt-verusage/tests/test_hint_augmentation.py \
  skillopt-verusage/tests/test_fork_packets.py \
  skillopt-verusage/tests/test_fork_card_optimize.py \
  tests/test_proof_progress.py tests/test_trajectory_progress.py \
  tests/test_trajectory_parsers.py tests/test_proof_dependencies.py
git diff --check
python3 research_memory/scripts/mem.py index
```

Actual tests used the available temporary pytest/PyYAML environment with pinned
native SkillOpt import path. Full commands are normalized above for portability.
Fresh generated runs only; historical dev01/dev02 preparation attempts remain
external and are superseded by dev03, not deleted or reinterpreted as final runs.

## Limits and next step

Rehydration supplies exact saved code and visible completed-observation history,
not a live session's hidden state. Offline progress remains text/reference overlap
plus diagnostics, not semantic completeness. Parser admission excludes some
otherwise interesting post-regression states; a future safe pre-error provider
can study these explicitly. Point usefulness requires real interventions and
leakage-safe600s evaluation, not these local checks. All models remain Pro; actor
max/1800s learning,600s downstream contract unchanged. No test/val reads, legacy
tree writes, raw input mutations, paid calls, commits or pushes in this turn.

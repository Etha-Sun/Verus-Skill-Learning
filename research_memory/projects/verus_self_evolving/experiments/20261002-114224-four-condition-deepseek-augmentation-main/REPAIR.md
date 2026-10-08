# Confirmed method-component repair before design review

## Objective and authority

The user authorized repairing confirmed discrepancies, with a full design
review to follow. This is an auxiliary/dev implementation pass, not renewed
paid-run authority. The old campaign remains stopped/reference-only. The
meeting-to-code interpretation is in `MEETING_ALIGNMENT_AUDIT.md`.

## Implemented and verified

- Removed the verifier-count/middle-checkpoint selector. Campaign input preflight
  now audits originals and reports verified-reference availability without
  writing a new frozen selection.
- Added `campaign_evidence.analyze_progress` and an offline
  `Campaign.prepare_progress` driver using the existing verifier-gated greedy
  pruning, fresh reference verification and Lynette preservation, target-proof
  line coverage, exact verifier snapshots and source output-token ledger.
  Reports contain the full curve, all plateau spans and coverage/tier drops;
  branch selection, ranking and K remain pending. Unsolved originals are retained
  with `no_verified_reference`, not assigned an invented reference or midpoint.
- Shared historical plateau/regression reporting with the existing analysis
  script rather than creating a different campaign metric. A drop is a textual
  or verifier-tier observation, not a proven semantic regression.
- Real-log inspection exposed two integration defects in the existing progress
  component: `run_verus.sh` calls were treated as host checks, and native
  Responses ledgers without input-item types assigned every tool to final cost.
  Fixed wrapper/source-tool identification and added completed-request timestamp
  alignment for that ledger format. Missing alignment metadata is rejected.
  Historical ledgers retain the input-item-delta path.
- Added fork-comparison views with exact original event/hash, hint hash, branch
  initial snapshot and original-task checks. Original prefix + original suffix
  reconstructs the original; prefix + actual hinted suffix is an analysis view,
  not a claim that the actor replayed the original conversation. Distinct event
  namespaces and intervention boundary are supplied; failed suffixes remain.
- Updated the card prompt to explicitly compare hint/fork state, changed actions,
  actual verifier outcomes, suffix convergence and costs, including negative
  branches. No unsupported causal savings claim is allowed.
- Removed unapproved two-card/700-byte/ASCII limits from request schema and
  host admission. Existing output-token/context/spend guards and card evidence,
  task-leakage, copied-proof and verification-bypass checks remain. Final length,
  count and exposure budgets are not yet frozen.
- Added an agent-visible index of every card's ID/title/trigger. An indexed card
  can be read directly without lexical search; search remains optional. The
  initial index does not expose card bodies or host-only provenance. This is
  an untruncated prototype index, not an agreed final exposure budget.
- Disabled paid campaign entry points pending design review, before preflight
  or guard/model calls. Old started campaigns cannot be reopened/overwritten.
  The legacy single-fork coordinator is retained but gated, not promoted as the
  corrected grouped method. No approval-boolean shortcut was added.

## Verification evidence

Environment: Python3.11.7, pytest9.1.1, PyYAML6.0.1; pytest was installed in a
temporary isolated venv, not the user's global interpreter. Specialized science
artifact/bash interfaces are unavailable; local execution, durable test log and
canonical repository memory are the explicit fallback. No graph nodes are claimed.

Regression command (using that interpreter):

```bash
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src python -m pytest -q \
  skillopt-verusage/tests/test_augmentation_campaign.py \
  skillopt-verusage/tests/test_card_bank.py \
  skillopt-verusage/tests/test_skill_artifact.py \
  skillopt-verusage/tests/test_skill_validation.py \
  skillopt-verusage/tests/test_codex_flash_runner.py \
  skillopt-verusage/tests/test_codex_deepseek_bridge.py \
  skillopt-verusage/tests/test_hint_augmentation.py \
  skillopt-verusage/tests/test_fork_packets.py \
  tests/test_proof_progress.py tests/test_trajectory_progress.py \
  tests/test_trajectory_parsers.py
```

Result: **93 passed, 13 subtests passed**,1.28s. Reproduction tests first failed
for the missing progress/comparison/index/gate behavior, hard card caps and both
native-ledger integration defects, then passed after repair. The offline driver
is tested end-to-end with mocked verifier/preservation subprocesses and asserts
no provider call. `git diff --check` passed.

External test log:
`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/method-alignment-repair-20261002-Be0SgK/pytest.log`.

Parsed existing-data check: all40 original source event/ledger adapters aligned
497 verifier calls with nonmissing, nondecreasing recorded cumulative output
tokens. This is only ledger/call adaptation, not forty real pruning runs, full
usage/billing completeness, validated checkpoint selection or method efficacy.
Source run ID: `train40-pro-initial-1800s-20261001-KjQXKA`.

## Pending design and remaining implementation

Subsequent user clarification: record learning costs; do not enforce the proposed
per-method/analysis budget stop. This resolves/supersedes that budget-policy
question below. The configuration-inspection turn records the direction only;
old runtime limit code was not changed, paid entry points remain disabled, and
the earlier global USD80 safety ceiling is not silently revoked. No value-ranking
or checkpoint selection policy exists beyond plateau/drop reporting, and no
actual40-source candidate-shortage count has been computed.

The code is **not ready for paid execution**. The multi-checkpoint/multi-branch
coordinator, related-source reflection batching and budget-frontier admission /
closure are not completed by these component repairs. Confirm the parameters
first; do not unblock the legacy coordinator by removing only its gate.

Immediate questions were sent to the user about:

1. Exact branch count and batch membership (meeting example3 hinted branches,
   original +3, two source groups in an eight-trace batch); insufficient eligible
   points and the final checkpoint ranking/threshold/fallback policy.
2. Matched monetary learning boundary, including original sampling, teacher,
   continuations, reflection, failures and closure; whether USD25 per method
   remains intended. The authorized total ceiling stays USD80. A future fresh
   campaign must explicitly account for prior diagnostic spend within the
   applicable authorization rather than assuming a fresh USD80 allowance.
3. Card count/length and initial index/body exposure budgets. The prior two-card
   and700-byte numbers are no longer silently treated as requirements.

The later complete design review must also cover main arms/repetitions, native
update/validation gate/epoch policy, role reasoning efforts/output caps,
no-verified-reference handling and whether older branches qualify for reuse.
Already explicit model and clock decisions are retained, not asked again:
DeepSeek V4 Pro for all roles; complete-path actors max/1800s; downstream600s;
fixed40/20/20 with test20 sealed. Current teacher/extractor high is not a new
all-role-max decision. A repaired component test is not main-result evidence.

## Safety and next action

Only scoped code/tests, reviewed compact memory and external test logs were
written. No provider call, real verifier pruning, new experiment, artifact
deployment, commit or push. Raw/sealed sources, original40, prior campaign
outputs/ledgers, transcript and test20 were not modified. Unrelated dirty
working-tree changes, including earlier bridge changes, were preserved.

Next: review the complete method contract with the user, implement the remaining
coordinator and matched-budget closure, verify a bounded train-only chain, and
obtain explicit restart direction before new paid execution.

# Dual trajectory parser branch and data contract

## Decision

Create `feature/trajectory-progress-parsers-20260908` from the fetched
`origin/main` commit `01d2f0b`, using a separate worktree because the original
`main` worktree has user changes that overlap upstream updates. Keep two input
adapters behind one normalized `verus-trajectory-v1` contract:

- `sonnet45` parses legacy terminal logs and exact paired input/final sources,
  but marks intermediate reconstruction as
  `partial_terminal_transcript`.
- `structured` parses recent `conversation.json`, `agent_events.jsonl`, result,
  workspace, snapshot, diff, and bridge-ledger artifacts; it marks intermediate
  candidates exact only when snapshot hashes align with the event stream.

This pass extracts evidence only. It intentionally does not define a progress
score or infer missing intermediate programs.

## Alternatives Considered

- One permissive parser for both formats: rejected because it would hide the
  material difference between rendered terminal edits and exact snapshots.
- Treat rendered Sonnet edit blocks as replayable patches: rejected because
  wrapped and collapsed terminal output cannot guarantee exact reconstruction.
- Switch or merge the dirty original worktree directly: rejected because nine
  locally changed paths overlap the fetched upstream delta.

## Evidence

- The readable standard Sonnet 4.5 training corpus contains 258 terminal logs:
  104 Anvil and 154 IronKV. Each has paired source and verified source files.
- The recent structured corpus contains 1,399 prediction directories below the
  external SkillOpt run tree and 217 more below the current ignored run tree;
  snapshot counts are 34,797 and 3,628 respectively.
- A real Sonnet smoke parsed 37 assistant messages, 24 reported code edits,
  nine other tool calls, and 22 verifier invocations while preserving the
  partial-fidelity warning.
- A real structured smoke found 19 exact candidate snapshots, all with hashes
  present in the event stream, and reconciled retained versus complete-ledger
  usage separately.
- Focused parser and usage tests pass 12/12. The repository test suite reaches
  113 passes and two pre-existing Trace2Skill vendored-runtime hash failures;
  this branch does not modify that vendor tree.
- Smoke outputs are stored under
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/trajectory-parser-smoke-20260908-v3/`.

## Risk

The main analytical risk is silently comparing incomplete Sonnet edit evidence
with exact structured checkpoints as if they had equal fidelity. The schema
therefore exposes `source_format`, `reconstruction_fidelity`, artifact hashes,
and checkpoint contracts. A local configuration risk also remains: the current
machine-local `VERUS_SKILL_RUN_ROOT` points inside the repository and fails the
repository data-layout contract; it must be redirected to the external run
root before new production parsing.

## Next Action

Review and freeze the normalized schema on a small stratified audit set, then
build a descriptive progress table separately for each fidelity tier. Only
after auditing missingness, verifier alignment, and checkpoint comparability
should the project define or validate a progress metric.

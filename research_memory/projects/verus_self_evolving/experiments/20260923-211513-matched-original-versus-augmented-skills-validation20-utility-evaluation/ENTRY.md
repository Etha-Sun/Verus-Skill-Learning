# Matched original versus augmented skills validation-20 utility evaluation

## Metadata

- project: `verus_self_evolving`
- kind: `experiments`
- created_at: `2026-09-23T21:15:13`
- status: `stopped_for_trace_audit`

## Objective and frozen design

The user authorized actual skill utility evaluation and asked whether API access
exists. A credential is stored locally outside the repository; an authenticated
DeepSeek model-list request succeeded and advertised the selected V4 Pro model.
No credential value is recorded here. Formal Verus, Lynette and Linux actor
isolation pass preflight after restoring the established Rust environment.

Primary conditions: initial skill, original-only three-task extraction, and
augmented extraction of the same three tasks. Secondary references: the provided
ordinary train-40 stage-1 skill and the prior Astra-reviewed augmented four-card
candidate. Both new matched extractions use the same Sol/high model, prompt,
initial skill, task weight one, at most two proposals per task, same native merge,
four-card cap and 4,000-byte limit. Both native candidates remain unedited and
receive the same evidence audit; the prior reviewed card is a separate condition.

Both matched extractions completed: four native calls each. Original-only
candidate is 3,357 bytes, SHA-256
`6205e0e03632ddb2960d78e3791b187517e36e0a7de0d95515f13ee57b6d38e2`;
augmented is 3,329 bytes, SHA-256
`7c3dec0fc48c06bedb2aa0e8156a98405715536f8d3ad2878ed8e48442bedc29`.
Each contains four cards and passed automatic shape checks. Complete input
copies and hashes are external; historical originals and continuations were
not rerun or modified.

Evaluation uses the unchanged validation-20 only, DeepSeek V4 Pro/high via native
Responses, current Codex CLI recorded by each run, formal Verus, one unchanged
static skill per condition, 600 seconds per task, and two independent repetitions
with no provider seed control. Five conditions produce 200 planned rollouts.
Pilot: first repetition on the lexicographically first ID in each of IR/AC/AL,
15 condition-task runs total; stop only for infrastructure/record validity, not
poor solved rate. Remaining tasks follow a frozen shuffled schedule. Skills
must be frozen before actor calls. No validation-driven card edits or test use.

Primary guard is within-budget dual-validation success. Report conditional
completion costs on jointly solved task/repetition pairs alongside all-run
usage, failures, timeouts, per-repeat outcomes and separately estimated actor
cost. Include failed-run usage; never interpret premature failure as efficiency.
Repeated runs on the same task are correlated. Extraction and teacher overhead
remain separate from downstream actor cost.

## Execution and safeguards

The new validation driver reuses the existing isolated actor runner. Actor
workspaces cannot read training traces, other skills/results, credentials, or
repository evaluation sources. API keys stay in the host bridge. Eight workers,
no automatic actor reruns, a shared USD 30 estimated-cost guard, and durable
per-task results/progress permit audit and continuation. This guard uses the
existing local price estimates, not a guarantee about current provider billing.

Inspection found native Responses forwarding ignored the shared budget guard;
that path now reserves before network access and settles actual or uncertain
usage afterward. Focused tests verify denial before network, success accounting,
unknown-cost retention, schedule coverage and failure-safe paired statistics:
30 tests and 4 subtests passed. The stream/request content is otherwise unchanged.

## Artifacts and current state

External root: `${VERUS_SKILL_RUN_ROOT}/skillopt-validation-20260923/`.

- `experiment_contract.json`, `runtime_config.json`, `implementation_hashes.json`;
- `extraction/original_only/`, `extraction/augmented/`, and frozen `skills/`;
- `preflight.json`, `audit/`, `matched_audit.json`, `frozen_skills.json`;
- `status.json`, `validation.log`, `results.json`, `summary.json`, `RESULTS.md`;
- `bridge_calls.jsonl`, `budget.json`, and full `rollouts/`.

At this record's creation, extraction and preflight were complete and independent
matched-candidate review was finishing; validation actors had not started.
Update status after launch and report actual completion rather than scheduled
counts. No raw/sealed data was modified. All run outputs remain external.

## Launch confirmation

Astra completed equal read-only review and recommended both native candidates
for validation without edits. The matched prompts, seed and budgets agree;
original-only has six proposals/four final cards, as does augmented. No explicit
cross-condition or validation reads were found in the recorded extraction
commands. Known merge/trigger weaknesses are retained as testable policies.
The approved skill hashes and review hash are frozen in `matched_audit.json`.

Validation is now running in an independent background process. The launcher
PID is recorded in `launch.json`; worker PID and current phase are in
`status.json`. At the first live check all eight pilot actors emitted trace
events with no error events, and the provider bridge had 35 settled requests
with no uncertain requests. This verifies live API use, not completed evaluation.
The runner saves each result and aggregate, advances only after pilot validity,
and writes `RESULTS.md` on full completion. It stops before further batches on
invalid infrastructure results, preserving partial runs for audit.

Current next action: monitor `status.json`, `validation.log`, and `summary.json`;
resolve any infrastructure stop without changing frozen skills or hiding failed
attempts. Final test remains untouched. Historical train traces and sealed data
remain unchanged; validation rollouts are new external outputs.

## Status check on 2026-09-26

No background run remains active. The first batch stopped after eight outcomes:
three dual-validator passes classified V0 because of trace-fidelity flags, and
five timeouts. No subsequent evaluation outputs or final RESULTS.md exist.
The provider ledger contains 234 settled requests; the partial actor spend is
recorded externally. This check made no inference calls and did not restart the
run. Diagnose incomplete-payload indexing before using the flagged records or
resuming; preserve all originals. No local GPU is permitted.

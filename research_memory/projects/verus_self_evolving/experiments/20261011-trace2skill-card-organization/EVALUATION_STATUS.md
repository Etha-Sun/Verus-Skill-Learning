# Compact grouped skill versus repaired78 flat control

Latest: user authorized remaining work. v5systemd continuation now runs16cells,
retaining24 prior results under the same cumulativeUSD30 ceiling. See
[CONTINUATION_STATUS.md](CONTINUATION_STATUS.md); older stop records below remain
historical evidence, not the current running status.

Audit completed, zero paid calls: see [ANOMALY_AUDIT.md](ANOMALY_AUDIT.md).
The late error occurred after a600s timeout; shared bridge latch prematurely
aborted a different task. The dual-pass V0_INVALID was a real cp editing-protocol
violation, not a failed proof. Classification/evidence-capture gaps identified;
frozen implementation and existing results unchanged. Recovery not launched.

## Latest: stopped on incomplete upstream response

Checked12:56UTC October12: service failed/exit1, summary finished10:52:51UTC.
25episode records exist (A13,B12),15not started. A native response for revised
0e8d3ca5b02dc01ee01f failed with IncompleteRead(1835121 bytes read); fail-closed
guard stopped the campaign. This is not the earlier detached process problem.
The duplicate failure messages refer to the same provider error. Ledger drained
and frozen inputs unchanged. No further paid calls launched at this status check.

Provisional budgeted dual-pass counts are A8 andB8. B's aa78e84a931f703c7e9c is
dual-pass but V0_INVALID trace fidelity, requiring audit. Additionally, the saved
provider_valid flags were not refreshed after the delayed provider failure:
revised0e8d... has settled unmetered/error evidence, while old9b9... terminated
with code1 and V0_INVALID after the shared error latch. Do not count these as
ordinary proof failures or claim that statistics.json is validity-reconciled.

V4 settled costUSD2.133143672; unknown-call boundUSD1.83904512; inherited charge
USD3.845267536. Conservative cumulative budget occupancyUSD7.817456328 of30;
not budget exhaustion. Known actual estimates and unknown bounds stay separate.
Next: audit validity/fidelity and request any new technical recovery authorization;
preserve existing results rather than rerun successful cells.

Earlier running-state notes below are superseded by this stop record.

## Current: systemd recovery running, USD30 overall cap

User explicitly authorized raising the cap to USD30 and re-running. Fresh40-cell
campaign is now managed by `verus-card-eval-20261012-v4.service` on vegeta's user
systemd manager, with Linger=yes and Restart=no. It does not depend on the local
computer, SSH connection, or CLI session. Server shutdown/service termination
can still stop it; no automatic restart or reboot recovery is configured.

Current output, relative to VERUS_SKILL_RUN_ROOT:
`skillopt-verusage/card-organization-evaluation-20261012-v4/`.

The new budget inherits USD3.845267536 conservatively: USD0.167177296 known spend
including review and USD3.67809024 bounds for two unresolved requests. Those
bounds are NOT asserted actual charges. Original v3 budget/ledgers/attempts are
unchanged and preserved; construction is still excluded from the evaluation cap.
All40 cells restart with identical packages, schedule, model, prompt, tools,
permissions and scoring. Earlier two infrastructure-interrupted attempts are
retained separately, not counted as proof failures or valid primary episodes.

Actual systemd zero-API preflight passed for both arms; ten recovery/evaluation
tests pass. First native actor calls completed successfully. Contract SHA256:
`77b7f43c52ef2020f0a15e58e51943a5071239c99e3503c69e4cae040f717374`.
The recovery's exact-hash review receipt is explicitly a coding-assistant
delta review based on user authorization and unchanged previously reviewed
methodology. It is not falsely attributed to DeepSeek or copied as a new model
approval. No extra paid review call. Implementation is a separate wrapper,
`scripts/recover_card_organization_evaluation.py`; original frozen sources remain
unchanged. See `recovery_delta.json` and `service_receipt.json`.

Monitor `evaluation.log`, `progress.json` after completions, and `budget.json`.
Do not launch another process or clear prior reservations. Await settled full
results before comparing effectiveness. Raw/sealed data and source skill files
remain untouched. Earlier chronology below is superseded by this section.

## Interruption correction

At the user's shutdown-safety check on 2026-10-12, the driver PID no longer
existed. Both actors report Broken pipe; no complete episode or final summary
exists. The exact reason for the driver exit is not established. The earlier
statement that launch succeeded was true at inspection, but did not establish
durability across the CLI connection lifecycle.

Preserve 2interrupted attempts and38unstarted cells. Settled spend including
review is USD0.167177296; two dispatched requests have no response/settled usage,
and retain total USD3.67809024 reservations. Do not count those as zero-cost or
clear their reservations automatically. User has been asked to approve technical
repeats with those bounds charged conservatively to the same overall USD20 cap.
No further paid calls have been launched.

Server user systemd is available. Current-user Linger has been enabled, so
services can remain after SSH logout. A five-minute sleep-only service probes
this execution path; no model calls. Recovery should use a systemd user service,
not the earlier nohup launch. Evidence: `interruption_audit.json` in the run root.

## Earlier launch record (superseded)

Updated: 2026-10-12. User explicitly authorizes 40 episodes and a shared USD20
evaluation ceiling, separate from USD1.74243608 construction. Current phase:
zero-API preflight and new DeepSeek V4 Pro/max contract review passed;
the 40-episode evaluation is running in a detached process. First pair has
started and completed native provider calls successfully; no final outcomes yet.
Review cost USD0.13711104 is included in the evaluation guard.

## Frozen configuration

| Item | Both arms |
| --- | --- |
| Data | Fixed validation20, not sealed test20 |
| Repetitions | One per task per arm; 40 fresh episodes |
| Actor | DeepSeek V4 Pro, max reasoning, native Responses |
| Budget | 600 actor seconds; 1048576 context; 131072 output per request |
| Provider timeout | 1800 seconds; does not replace the actor deadline |
| Parallelism | Two workers; alternating submission order by task |
| Prompt | Current shared corrected TASK; original Executive, not diagnostic-first |
| Library access | Same installed vstd path, read-only for both arms |
| Retry | None automatically, including transport failures; halt for audit |
| Cost | Shared conservative request reservations; unknown cost blocks dispatch |
| Success | Provider-valid, Verus solved, proof-only safety passed, within 600s |

A is the unchanged published repaired78 flat short-index package, SKILL11545bytes.
B is the reviewed compact-v1 grouped/reduced package, SKILL7957bytes, 37references,
72rules covering 78source cards. No online router or mandatory retrieval added.
The original construction manifests remain immutable; this new evaluation
contract records the later authorization separately.

## Environment disclosure

Codex0.147.0, Lynette, and model catalog match historical SHA256 exactly.
Verus reports 0.2025.09.12.bb1f342 in both environments, but rust_verify differs:

- Historical: `c1100e7aea575799693b97deabe7c2abc4ce8bdb78f1ffdbb610b8c8ab66c650`.
- Local: `aefa9c80d1a9638070c5111f36455400c10605e1b312848fb326fe2b82c7e8a3`.

User explicitly accepted this difference, provided both new arms share the local
toolchain and the report discloses it. Thus this is a controlled contemporaneous
comparison, not a bit-identical reproduction of historical runs. The historical
evidence is the published manifest in archive executive-single-20261010-I5C6Z6,
session-000/dev_old--08d1a2c2d3839f127970--repeat-0, SHA256
`8c5b1f36d639f915a54168415132a76295fd2cd85bcaf76db884c95d4bfdad13`.

## Checks and implementation

- 142 related offline tests pass, including eight new evaluation wiring and
  scoring tests, existing bridge/artifact/runner tests and five isolation tests.
- Real isolation probes pass for both bundles: private files hidden, external
  network blocked, vstd readable but not writable, legal Verus/Lynette dual pass.
- All78 card readers and all37 reference readers succeed inside isolation.
- Real Codex executable reports0.147.0 inside both isolated workspaces.
- Thin wrapper: `scripts/evaluate_card_organization.py`; reused runner:
  `scripts/validate_card_revision.py`, with additive budget/auditor injection,
  optional explicit Rust root, and optional repository dotenv fallback.
- Contract pins package bytes, sources, shared TASK, catalog, runner sources,
  Verus dependencies and Rust compiler. Review receipt binds its exact hash.
- The entire A bundle (not just SKILL.md) matches historical SHA256
  `4f571411bdd9667db0b356b973592b9b161add4326d5f4b6f17a940c05404635`.
  B bundle SHA256 is `7055acd4f2e37f9213c54441a945bb6ea4696fd2194e7932f3b2989416cf139a`.
- Two earlier zero-API attempts are preserved: v1 probe command mismatch;
  v2 sandbox loopback permission denial. Neither made provider calls.

## Contract review disposition

Decision: APPROVE_WITH_NONBLOCKING_NOTES, no blocking issues. Preserve the raw
response and original receipt, including these reviewer limitations:

1. Review spend sharing the USD20 ceiling is intentional and documented.
2. The inherited `card_bank.audit_retrieval` already flags flat-arm direct
   `cards.json` commands; the wrapper adds reference commands symmetrically.
   Neither command matching nor returned content proves semantic application.
3. The reviewer received the wrapper/driver sources, not every hashed imported
   module. Offline inspection confirms the native bridge's single dispatch,
   error latch and capture-before-status handling;84 bridge/runner/artifact tests
   pass. Driver failure stops further scheduling. No paid actor retry is added.
4. The review incorrectly states preflight.json is not hash-bound: its resolved
   path and SHA256 are present in contract input_hashes; verified directly.

The first live pair independently confirms matching TASK hashes, Pro/max,
600seconds, detailed reasoning, vstd read-root and actor isolation. Both deployed
bundle hashes match the frozen contract. Four initial provider responses reported
completed status and upstream model deepseek-v4-pro with no provider errors.

## Evidence and resumption

All following paths are relative to VERUS_SKILL_RUN_ROOT:

- Current evaluation: `skillopt-verusage/card-organization-evaluation-20261012-v3/`.
- Contract: `validation_contract.json`, SHA256
  `646ee1131fab0c4db1091c605edc6e14b74ccc975a3c4305a9230fb8a1dd0d93`.
- Zero-API evidence: `preflight.json`; frozen packages: `bundles/old`, `bundles/revised`.
- Verified historical evidence copied from the published archive:
  `historical_run_manifest.json` (hash checked against the publication manifest).
- Reviewer evidence: `review_calls/`, `review_provider_calls.jsonl`, `review_receipt.json` when completed.
- Live evidence once started: `progress.json`, `provider_calls.jsonl`,
  `provider_capture/` (shared with the reviewer; request IDs identify each call),
  `episodes/`, `full_traces/`, `budget.json`.
- Detached process evidence: `launch.pid`, `evaluation.log`. Progress is written
  after episode completions, not after every provider response.
- Settled analysis after bridge drain: `summary.json`, `episodes.csv`,
  `task_pairs.json`, `statistics.json`.

Do not automatically re-run a stopped/failed actor or re-use this output root.
Check process state, provider ledger and all cost reservations before resuming.
Direct/partial reference file reads require trace audit; helper event absence
is not evidence of no reading. Returned content is exposure, not causal use.
Report all-attempt resources, success-only and joint-success resources separately;
paired task bootstrap uses10000 resamples, seed20261006. Already-used validation
data and single repeats preclude claims of independent efficacy confirmation.
Raw datasets, sealed test data, source cards and original candidate are unchanged.

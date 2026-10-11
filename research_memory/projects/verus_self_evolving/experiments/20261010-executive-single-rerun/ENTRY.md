# Fresh single-repeat validation20 Executive comparison

User requests rerun40episodes after clarifying dataset/count and prior results.
Interpreted explicitly as validation20xold/newExecutive,onefreshrepeat,not40new
problems. Supersedes proposed80continuation: do not reuse26valid prior outcomes.
All prior snapshots/runs preserved. No prompt/card/budget/model change.

## Contract and artifacts

External:VERUS_SKILL_RUN_ROOT/skillopt-verusage/executive-single-20261010-I5C6Z6/.
validation_contract.json SHA256:
a26568e4a137907f75d1cc7b5f05ad50c77b8a7ce75edfb276cbf0081fae9d42.
Same fixed val20/Pro max600s/two workers/repaired78bank/index/reader/vstdpermission
and common correctedTASK; only initial versus diagnostic-first Executive differs.
One unique cell per task/arm; no second stochastic repeat or historical reuse.
See PLAN.md and CHECKLIST.md. Development-only, not untouched test or augment ablation.

New script scripts/single_executive_validation.py composes full40/80
preparation/executor helpers. Astra rejected first contract c534cac7...6318e:
shared executor submitted two initial jobs even if only one recovery cell remained.
Fixed one scheduler line to cap initial submissions by schedule length. Opt-in
preparation accepts this scheduler-only drift only when reversing that exact line
restores the frozen pilot driver SHA; all other drift is rejected. Old/current
digests are recorded in scheduler_only_updates. No scientific input changed.
Rejected prepared root executive-single-20261010-TW8Yzo is preserved with no calls.
Fail-closed bridge is not weakened; after a drained
session, reuse settled valid outcomes and replace only proven IncompleteRead
invalids via existing evaluate_resume.transport_retryable. At most2bridge restarts,
at most2attempts per cell. Ordinary proof failure/600stimeout never replayed.
Late unmetered/provider errors cannot be admitted just because final proof passes.
Every session keeps contract, summary, ledger, events, full exports; parent summary
selects40unique admitted cells and reports all-attempt costs/unmetered caveat.
No replay of uncertain session with no summary, drain or matching contract hash.

## Commands and verification

Prepare: vrl Python scripts/single_executive_validation.py --prepare --config
RUN_ROOT/skillopt-verusage/train38-hindsight-native-20261007-aQfE7o/config.json
--pilot RUN_ROOT/skillopt-verusage/executive-pilot-20261009-NYYmFA
--audit-source RUN_ROOT/skillopt-verusage/executive-full-20261010-YUSsK2/pilot_audit/audit.json
--output EXTERNAL_ROOT. Environment VERUS_SKILL_RUN_ROOT external,
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt.
Run replaces prepare/pilot/audit options with --review EXTERNAL_ROOT/review.json.
Exact launch argv/PID/environment overrides will be in launcher.json.
Active progress: active_session.json points to sessions/session-*/progress.json;
root summary is a settled checkpoint, not a live per-episode counter.

99combined tests pass:40cell preparation, complete matrix, bounded replacement,
no outcome retry (including timeout), resume checkpoint replay without new calls,
late-provider rejection, nontransport/exhaustion stopping, prior wrappers/gate.
Includes actual shared-driver singleton collection and39admitted/1replacement,
plus rejection of unrelated parent method drift;82of99tests cover recovery/runner.
Existing transport predicate independently returnsTrue on both actual previous
invalid6a728rows. Diff clean, disk1.9TBfree.
Fresh Astra APPROVE_WITH_NONBLOCKING_NOTES on exact a26568e4...ae9d42 contract;
independently verified50hashes and ran55tests. See review.json; old receipts unused.

## Launch

Started2026-10-10T06:54:25.355639Z, PID4007184, detached full40queue. Generated
launcher.json records argv/safe environment overrides/receipt hash. Confirmed
alive in host launch namespace, session-000 first aded old/revised actors both
producing CLI events,5actual dispatched provider records and empty actor stderr.
No completed episode at startup; this is not a new efficacy result. Bounded
transport recovery and selected40matrix/stratum summaries run automatically.
No additional paid smoke run. Process lookup inside default sandbox cannot see
this host process; use host namespace for liveness, not a false missing-PID claim.

## Status and evidence boundary

Completed2026-10-10 01:49:16Pacific,114.85minutes after launch. Results checked
2026-10-10 11:32Pacific. See RESULTS.md for metrics, paired census and evidence.
40unique provider-valid cells,855settledrequests,0upstreamerrors/unmetered,
all50inputs unchanged; session summary/ledger hashes match. No recovery needed.
Initial14/20versusnew15/20;14bothpass,5bothfail,1gain(a23a),0loss. Actor time
+7.28%,prompttokens+3.98%,cost+5.05%; totalestimatedUSD5.225239448. Pilot6:
3/6vs4/6;remaining14:11/14both. More card-body readers2->4,notcausalbenefit.

evaluation_summary: complete40freshcells,metric_and_ledger_audit_complete;
claim_update: small+1pass,efficiencyworse,broadbenefitunproven;
baseline_relation: fresh40matchedcomparison, same method/one repeat;
failure_mode: previousHTTPtransport failure, bounded recovery implemented;
next_action: read-only case audit sole gain, both-pass slowdowns and recurrent
both-fail tasks; no new paid run, code/prompt/card change in this result check.

Raw/sealed/legacy and old result files unchanged. Only new external outputs and
compact canonical repo memory. bash_exec/artifact APIs absent, shell/hash/memory
fallback without evidence-graph registration claim. No commit requested.

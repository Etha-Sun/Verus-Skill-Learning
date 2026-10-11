# Executive full validation development comparison

User authorizes autonomous scale-up after pilot inspection. Test the same
diagnostic-first Executive versus initial Executive on all fixed validation20,
two fresh repeats per arm (80 episodes), Pro/max/600s/two workers. No reuse of
pilot outcomes, prompt/card edits, forced retrieval, model substitution or test
access. Costs record-only. Null: no consistent benefit beyond selected pilot
tasks; alternative: improvement extends to the other14 analyzed validation tasks.
This remains development evaluation, not untouched test or augmentation ablation.

Primary: within-budget Verus AND Lynette pass. Secondary: final dual-pass,
timeouts, actor time, settled token/cost/error counts, read calls; results by
repeat and pilot6/remaining14. No independent-sample significance claim from
40 repeats/arm: only20unique tasks and all validation is previously exposed.

## Implementation and verification

1. Local analysis script audits all24 saved pilot command traces and supplied
   trusted blocks across snapshots; inspect all4timed-out episodes and both
   reader episodes. Verify no raw/frozen input mutation; save hashes and findings.
2. Add standalone full-validation wrapper using unchanged shared executor and
   byte-exact pilot bundles. Do not edit pilot script/methods (retain old hashes).
   Freeze80unique keys, reversed arm order on repeat1, same TASK/permission;
   tests cover schedule, hash/package comparison and incomplete/duplicate gate.
3. Fresh Astra receipt of exact contract, then launch durable queue. No extra
   paid smoke needed: pilot has already exercised this runner path24times.
   Monitor actual provider health; stop on infrastructure/provider/hash failures,
   not ordinary timeouts. No retry or mid-run tuning.

Operational compliance flags (toolchain introspection, environment inspection,
outside scratch experiments) are separate from terminal proof validity. Pilot
commands show such flags in both arms; do not hide them or certify strict scope
from Lynette. No reference/sealed access observed in reviewed commands. Audit
full run similarly before final interpretation; do not broaden permitted access.

## Evidence and runtime

External root under VERUS_SKILL_RUN_ROOT/skillopt-verusage/executive-full-*;
pilot_audit/, validation_contract.json, review.json, launcher.json, run.log,
progress.json, provider_calls.jsonl, full_traces/, summary.json,
full_executive_summary.json. Disk1.9TBfree; CPU/localtools+remoteAPI, noGPU.
Two-worker actor upper bound6h40m plus drain/export; typical about3-4h if
pilot times extend, no guarantee. Keep originalbanks/raw/legacy/sealed read-only.
bash_exec/artifact APIs unavailable; shell/hash/memory fallback, no graph claim.

Minimum: all80 valid, settled and input hashes unchanged. Solid development
evidence: per-task repeated behavior and remaining14 direction agree without
hidden compliance failures. Maximum: later untouched-test study, deferred and
not implied by user authorization to scale validation. Next: interpret all
outcomes and residual cases, then promote/revise/stop from measured evidence.

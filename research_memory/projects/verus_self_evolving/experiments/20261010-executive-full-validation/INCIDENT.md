# Provider transport interruption: partial run, not complete validation

Checked at2026-10-10T06:30:30Z. Driver stopped and exported partial evidence at
2026-10-10T06:20:21.549512Z, about63minutes after launch.28/80episode records,
26provider-valid (13matched task pairs),2invalid in first repeat task6a7283f1b8a3f1d862db.
Second repeat not begun. full_executive_summary.complete=false;
settled_provider_valid=false;bridge_drained=true;frozen inputs unchanged.

## Cause and exact boundary

Revised6a728 request96008d9b3c79477aa1bdaf6f0beda5b8 was upstream-dispatched,
then failed after0.649s with IncompleteRead(4083bytes read). No usage/finish_reason
returned; public capture incomplete. This establishes an HTTP response-read
failure, not its precise remote-provider versus intervening-network origin.
Fail-closed bridge halted; concurrently scheduled old6a728 produced0provider
requests and is also invalid. Revised final proof/safety happen to pass, but its
provider/terminal validity fails, so exclude this result from valid comparison.
Not caused by expense cap/disk/ordinary actor timeout; no retry yet.

## Partial outcomes (do not generalize)

Valid-only budgeted dual-pass: initial11/13, revised9/13. Valid actor timeouts:
initial2,revised4. The raw partial aggregate shows11/14versus10/14, but includes
both invalid episodes, including revised's passing final candidate; that is not
the valid comparison.13pairs are only a prefix of fixed validation20 repeat0,
not complete validation or a statistically stable regression claim. Pilot
advantage has not replicated in this prefix; do not hide this negative evidence.

Recorded metered estimated spendUSD2.529861752, including invalid attempt's
completed calls. One dispatched error request is unmetered with no usage;
despite unknown_cost_requests=0 in current counter, complete cost accounting
cannot be claimed. Actual provider billing for that request remains unknown.

## Evidence and recovery handoff

External:VERUS_SKILL_RUN_ROOT/skillopt-verusage/executive-full-20261010-YUSsK2/
{progress.json,summary.json,full_executive_summary.json,provider_calls.jsonl,run.log}.
All partial traces and frozen contract preserved. No new provider calls, runner
edits or recovery launch during this status inspection; raw/legacy/sealed intact.

Next: implement/review an infrastructure-recovery continuation without changing
scientific recipe. Preserve26valid episodes; remaining54cells include rerunning
the2infrastructure-invalid cells and52not-started cells. Explicitly distinguish
infrastructure replacement from ordinary outcome retries; keep normal600s
timeouts, negatives and costs. New continuation contract/receipt must bind the
preserved prefix and unchanged method. Do not overwrite/relabel this incomplete
run as complete. Then aggregate a unique80cell matrix and inspect regressions.

evaluation_summary: partial/stopped26validof80;
claim_update: broader Executive benefit remains inconclusive, partialprefixnegative;
baseline_relation: unchanged matched method so far, incomplete scope;
failure_mode: external_dependency/HTTPtransport under fail-closed bridge;
next_action: reviewed resumable continuation, not blind full restart or hidden retry.

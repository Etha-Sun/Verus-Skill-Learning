# Completed pilot: diagnostic-first Executive

## Scope and integrity

24/24 fresh episodes complete, six purpose-selected seen validation problems,
two repeats per arm, Pro/max/600s/two workers. Finished 2026-10-10T00:05:41Z
(2026-10-09 17:05:41 America/Los_Angeles), about61minutes after launch.
All30 frozen input hashes remain unchanged. Ledger matches summary hash;
bridge drained, failures empty.874metered requests, all upstream deepseek-v4-pro,
all finish_reason completed;0error/unmetered/incomplete/unknown-status/unknown-cost
requests. BrokenPipe log entries occur in timeout runs after actor disconnection;
no settled upstream errors. Normal actor timeouts remain in denominator.

External evidence: VERUS_SKILL_RUN_ROOT/skillopt-verusage/executive-pilot-20261009-NYYmFA/
{summary.json,executive_summary.json,provider_calls.jsonl,full_traces/}.
summary SHA256:1cbdd35010e862a0c407c8864e131f84b7d11d78ee01ce1d11a27feaa9d0fea0.
ledger SHA256:901b81c90bf86aae41a1be1483c0866c5bbc199f8af38b08c397382317f4144b.

## Aggregate result

| Metric | Initial Executive | Diagnostic-first |
|---|---:|---:|
| Budgeted Verus+Lynette pass |9/12|11/12|
| Final dual-pass including timeout validation |10/12|11/12|
| Actor timeouts |3|1|
| Actor seconds, sum |4092.825|3069.678|
| Prompt tokens, cumulative billed request inputs |28179978|21785083|
| Completion tokens |449064|320782|
| Reasoning tokens, subset of completion |360501|254733|
| Estimated provider USD |1.734913576|1.342586212|
| Body-read episodes / calls |0/0|2/7|

Within-budget success is +2/12, not three solved problems. Actor seconds -25.0%,
prompt tokens -22.7%, completion -28.6%, reasoning -29.3%, cost -22.6%.
Total estimated spend3.077499788USD. Prompt tokens include repeated context/cache
hits, not unique content. Cost is ledger-derived estimate, not a reconciled invoice.

## Complete task census

Each cell is budgeted pass count across two repeats. Mean actor seconds include
timeouts and are descriptive, not matched-success efficiency estimates.

| Task ID / topic | Initial pass | Revised pass | Mean actor seconds initial / revised |
|---|---:|---:|---:|
|aded79905be896942897 / quantifier trigger|1/2|1/2|521.2 /442.7|
|a23a4969155913255f76 / entailment equivalence|2/2|2/2|306.8 /210.1|
|3ce00a38706256ab00ea / trusted lemma chain|2/2|2/2|141.9 /57.6|
|9b9f6ccef89db4103c7f / unpack conditions|1/2|2/2|370.4 /181.8|
|b9e5384e929589f7b0cd / matching pod request|1/2|2/2|581.9 /551.2|
|599792dd13f472f45fa4 / always distribution|2/2|2/2|124.2 /91.4|

Repeat0:5/6 versus5/6. Repeat1:4/6 versus6/6. Paired episode census:8both pass,
3revised-only pass,1initial-only pass. Quantifier problem swaps winner between
repeats; it is not reliably fixed. Matching-pod initial repeat1 is final dual-pass
but actor timed out, so it does not count as budgeted success.
Two revised readers: a23a repeat0 reads020/029/056/058/077;9b9f repeat0 reads006/058.
Read counts do not establish adoption or causal benefit. Other revised passes
occur without body reads; cannot credit this gain to learned card retrieval.

## Interpretation and next route

evaluation_summary: complete valid development pilot with favorable aggregate
direction; claim_update: promising but inconclusive for stable/general benefit;
baseline_relation: incremental Executive effect under common corrected TASK and
same bank/index/reader/permissions; failure_mode: residual stochastic quantifier
timeouts; next_action: inspect residual failing and paired improvement traces,
then propose fresh full validation20 with unchanged recipe, not automatically run.

This does not test augmentation versus nonaugmentation. Both arms share task
scope/syntax repairs, so cannot isolate their historical effect. Selected seen
tasks and only two repeats do not support held-out solved-rate/significance claims.
No causal explanation from aggregate speed/read counts. Outside-vstd access and
trusted-background preservation beyond terminal Lynette require separate actual
command/edit audit; not certified by current aggregate checks.

Full traces retain saved prompts, CLI actions and captured public provider rounds;
exporter marks full_provider_conversation_complete=false and saves explicit gaps.
Public payload completeness is not complete hidden thinking or exact wire bytes.
No new provider call or run launched to inspect these results. Raw/legacy/sealed
data, old banks and frozen historical runs unchanged.

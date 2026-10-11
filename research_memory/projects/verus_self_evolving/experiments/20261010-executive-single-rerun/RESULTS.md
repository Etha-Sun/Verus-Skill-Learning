# Fresh validation20 Executive comparison results

## Outcome

Complete40/40:20validation problems x initial/diagnostic-first Executive x one
fresh repeat. Same corrected TASK, repaired78bank/index/reader, installed-library
permissions, DeepSeek V4 Pro/max/600s/two workers. No historical result reuse.
Started2026-10-09 23:54:25Pacific; finished2026-10-10 01:49:16Pacific,114.85minutes.

| Metric | Initial | Diagnostic-first |
|---|---:|---:|
| Within-budget Verus+Lynette pass | 14/20 | 15/20 |
| Final dual pass | 14/20 | 15/20 |
| Ordinary600s timeouts | 6 | 5 |
| Mean actor seconds, all20 | 319.49 | 342.75 |
| Actor seconds total | 6389.84 | 6854.97 |
| Prompt tokens, billed request sum | 14,503,327 | 15,080,213 |
| Reasoning tokens | 274,854 | 289,247 |
| Provider requests | 422 | 433 |
| Estimated provider cost USD | 2.548294496 | 2.676944952 |
| Episodes reading card bodies | 2 | 4 |
| Card body reads | 6 | 11 |

New versus old:actor time+7.28%,prompt tokens+3.98%,reasoning tokens+5.24%,
estimated cost+5.05%. Total recorded estimateUSD5.225239448.855requests all
metered/settled,0upstream attempt errors,0unmetered/unknown costs. One session,
40physical episodes, no transport replacement needed. Charges are provider
usage-based estimates, not a reconciled invoice.

## Paired census and strata

14both pass,5both fail,1new-only pass,0old-only pass. Only gain:a23a4969155913255f76
(vrs_rely_condition_equivalent_to_lifted_vrs_rely_condition),old600.36s timeout,
new502.70s pass. Both consulted bodies:old020/029/077,new029/056/070. Reading
different cards is observed exposure, not evidence that one card caused success.

Previously selected pilot6:initial3/6,new4/6. Remaining14:11/14both arms.
Thus aggregate+1pass is entirely within the previously analyzed pilot subset;
there is no solved-rate gain on remaining14in this one repeat. The earlier
pilot's approximately25%time saving did not replicate across full validation20.

Both-fail IDs:aded79905be896942897,3f17ea7c76a0ce99c098,
0e8d3ca5b02dc01ee01f,08d1a2c2d3839f127970,b9e5384e929589f7b0cd.
All11unsolved episodes are ordinary timeouts, not invalid provider failures.

Selected both-pass slowdowns for follow-up, not causal findings:

| Task ID | Initial seconds | New seconds | Body reads, old/new |
|---|---:|---:|---|
| b97aaebc64493c607210 | 216.3 | 520.8 | 0/0 |
| 599792dd13f472f45fa4 | 133.7 | 350.4 | 0/0 |
| 31ee3310a4aaede08658 | 262.2 | 438.7 | 0/0 |

These three slowdowns do not involve card-body reads; direct read-tool latency
cannot explain them. Index/prompt influence and stochastic proof exploration
remain hypotheses until full-trace audit. Fast gains also exist, e.g.331082
386.7->149.5seconds with new003/006/074reads and9b9f433.6->225.0seconds
without body reads. Neither correlation establishes card causality.

## Verification and evidence

Parsed completed summaries; independently computed20pair census/resource deltas.
Verified40unique expected keys, every selected row provider-valid, all requests
settled,50input hashes unchanged, child summary and ledger hashes match checkpoint,
one40episode session and40full_trace export directories. Trace directories retain
their own completeness metadata; export count does not certify hidden reasoning
or operational access compliance. No manual full-trace case audit this turn.
Log BrokenPipe exceptions occur at downstream response writing after native
upstream forwarding; they did not produce upstream ledger errors or invalid
episodes, and must not be confused with prior IncompleteRead transport failure.

External evidence:
VERUS_SKILL_RUN_ROOT/skillopt-verusage/executive-single-20261010-I5C6Z6/
- validation_contract.json:a26568e4a137907f75d1cc7b5f05ad50c77b8a7ce75edfb276cbf0081fae9d42
- single_executive_summary.json and summary.json:selected40matrix/resources/strata
- sessions/session-000/summary.json:finished/drained/failures/rowevidence
- sessions/session-000/provider_calls.jsonl:855settledphysicalrequests,
  SHA8050be78a6a5f89d15f119b093d1b5d036208723c4355d84162f315b895b75a7
- sessions/session-000/full_traces/:40exports with completeness metadata

## Interpretation and next action

Small observed solved-rate increase(+1/20,+5percentage points), modest resource
regression, no gain on remaining14. Insufficient to claim broad efficiency or
robustness improvement; do not promote diagnostic-first as proven better based
on this run. One previously exposed validation repeat, not independent test or
augmentation-vs-noaugmentation evidence. No causal card benefit established.

Next:read-only full-trace case study of sole gain, selected slowdowns and recurrent
both-fail tasks before proposing prompt/retrieval changes. No code/prompt/card
modification or new paid run authorized by this status report. Previous interrupted
run remains parked with no reused outcomes. Raw/sealed/legacy/frozen evidence
unchanged; canonical repo memory/index only updated. Science artifact/bash_exec
APIs unavailable; shell/hash/durable-memory fallback, no evidence-graph claim.

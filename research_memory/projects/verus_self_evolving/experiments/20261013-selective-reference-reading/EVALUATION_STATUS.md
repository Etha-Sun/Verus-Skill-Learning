# Selective-reference evaluation launch

2026-10-13: user explicitly authorizes a new USD30 evaluation and persistent
server execution because their local computer will shut down. Follow-up confirms
the existing unchanged grouped B versus selective-v2 C combined intervention,
NOT a newly navigation-matched control and NOT repaired78 flat A.

## Running

- Server: vegeta; service: `verus-selective-eval-20261013-v1.service`.
- systemd user service active/running, initial MainPID1537476; Linger=yes,
  Restart=no, KillMode=control-group. Local shutdown/SSH disconnect does not stop
  this service. Server failure/reboot or fail-closed provider/budget errors can;
  no automatic paid retry or reboot resume is configured.
- Fixed validation20,20fresh B+20fresh C,one repeat,600s actor budget,2workers,
  alternating condition submission by task. No old evaluation cells reused.
- DeepSeek V4 Pro/max, native Responses, detailed reasoning,1048576 context,
  131072 output cap/request,1800s provider timeout. Both live first-episode
  manifests confirm model,effort,600s and intended package identities.
- Credential file remains `Trace2Skill/.env.deepseek`; no secret logged/copied.
- USD30 is the new campaign's shared ceiling with zero inherited spend; current
  uncertain charges/reservations remain conservatively occupied. Previous
  completed evaluation and construction are outside this new campaign.
- First B/C task pair started; first5 provider calls settled with usage and
  zero error attempts at launch audit. This is not a promise of future uptime.

Run suffix under VERUS_SKILL_RUN_ROOT:
`skillopt-verusage/selective-reference-evaluation-20261013-v1/`.

## Freeze and preflight

Contract SHA256:
`ee36426b5725bd0aa9eaff500a71c55a6c19a8de436f2de30d41610cf4080566`.

B package hash:
`7055acd4f2e37f9213c54441a945bb6ea4696fd2194e7932f3b2989416cf139a`.
C package hash:
`26a12f232edd33e36347dba7e5975b44e0c5720967f996920507f5078eb44ed2`.

59 offline tests pass across package construction/revision, evaluation payload
audits, prior runner wiring and settled-result dimensions. New zero-API systemd
preflight passed37 B and146 C reader probes, Verus+Lynette dual validation,
isolated Codex0.147.0, private-file hiding, vstd read-only and actor external
network blocking. Workspace skill immutability uses the existing instructions
and post-run integrity checks, not a newly different permission policy.

Corrected TASK hash equals the previous recommended TASK; Codex/Lynette/catalog
match historical hashes. Local Verus0.2025.09.12.bb1f342 retains the previously
authorized historical rust_verify build deviation, identically in both arms.
All frozen inputs were hash-checked after live calls started.

Launch review receipt is explicitly coding-assistant wiring review under new
user authorization, not an independent DeepSeek review or reused Astra receipt.
Candidate build manifests remain immutable historical records with review-only
flags; the new run's hash-bound contract/receipt records evaluation authorization.

## Reporting safeguards

New wrapper `scripts/evaluate_selective_references.py` reuses the frozen prior
actor, TASK, transport, judging and scheduling implementation. Historical code
was not edited. `probe_selective_package.py` only performs zero-API preflight.

Reader audit recognizes both v1 whole-reference payloads and v2
index/read_single/read_rules/read_full. It validates payload text/hash/source
IDs against the frozen package, counts directory exposure separately from body
exposure, and records content/serialized bytes, tool calls, multi-read and
fallback events. Direct file/listing/search commands are flagged for manual
extent review; they are not automatically treated as full reads. Helper-only
directory conversion is not overall abandonment when direct access exists.

After provider drain, report proof dual pass, V2 compliance, provider completeness
and editing violation separately. Incomplete billing remains explicit; paired
resource aggregates use complete-billing task pairs instead of zero imputation.
Use the historical uniform-price comparison and task bootstrap10000/seed20261006.
Reports include all attempted primary cells, including timeouts.

Unchanged known limitation: public-capture mode may not retain the partial body
of an HTTP IncompleteRead. Provider failure still stops new dispatch; do not
claim this transport limitation has been repaired. Preserve any stopped run and
unknown reservations; never automatically replay a timeout/protocol violation.

## Inspect status

```bash
systemctl --user status verus-selective-eval-20261013-v1.service
```

Run files:

- `evaluation.log`: durable stdout/stderr, starting/finished/complete events.
- `progress.json`: completed episode count and failures, created after first finish.
- `budget.json`: settled/unknown/reserved estimated spend; reservations are not bills.
- `provider_calls.jsonl` and `provider_capture/`: provider accounting and raw evidence.
- `service_receipt.json`, `preflight.json`, `validation_contract.json`: launch evidence.
- `summary.json`, `report.json`, `episodes.csv`: final settled results after drain.
- `episodes/*/retrieval_audit.json` and `full_traces/`: post-run read/transcript evidence.

No raw/sealed data, old candidates, control source or previous run results changed.
Do not change any frozen evaluation input or launch a duplicate service while
this run is active. Next action: monitor existing service, not start another run.

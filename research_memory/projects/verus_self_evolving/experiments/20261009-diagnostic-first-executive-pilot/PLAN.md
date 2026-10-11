# Diagnostic-first Executive development pilot

## Objective and contract

Test whether the diagnostic-first Executive reduces the observed scope/syntax/
unsupported-API detours, without degrading the two positive controls. Null:
no consistent improvement over initial Executive; alternative: repeatable repair
of these failure modes with no control regression. This is auxiliary/dev work,
not untouched evaluation or an augmentation ablation.

Six already-analyzed fixed validation tasks: aded79905be896942897,
a23a4969155913255f76, 3ce00a38706256ab00ea, 9b9f6ccef89db4103c7f,
b9e5384e929589f7b0cd, 599792dd13f472f45fa4. Run both arms twice (24 fresh
episodes), DeepSeek V4 Pro/max/600s, two workers. Same corrected TASK prompt,
repaired78 bodies/index/reader, autonomous optional reads and exact installed
vstd permission. Only Executive seed differs. Costs record-only. No answer,
reference proof, training, sealed test, ordinary retries or forced retrieval.

Primary endpoint: within-budget Verus AND Lynette pass. Also report final pass,
timeouts, actor seconds, settled input/output/reasoning usage, cost, body reads
and trace behavior. Repetitions are not independent new problems; no inferential
solved-rate claim or significance test from this purpose-selected sample.

## Minimal code change and verification

1. Add optional repeat suffix to shared driver episode keys, preserving every
   historical key when repeat is absent. Add a small Executive-specific wrapper.
   Verify unique 24-key balanced schedule and unchanged old defaults.
2. Freeze byte-exact card/reader/index equality, corrected TASK and method hashes.
   Verify local tests and obtain fresh Astra receipt of the exact contract.
3. Launch durable external run, verify actual provider start and healthy progress.
   Preserve full trace/payload/ledger output and aggregate complete schedule only.

Use existing runner/bridge/isolation, not a new execution engine. Minimum evidence:
24 valid episodes with all hashes unchanged. Solid development evidence: consistent
per-task repeated results plus full-trace confirmation of intended behavior.
Maximum (deferred): validation20 only after interpreting pilot, no automatic launch.

Stop on provider-invalid/infrastructure failure or changed frozen inputs. Normal
600s timeout is an outcome, not a retry condition. Preserve failed runs; ask before
materially changing model or protocol. No retuning during execution.

## Runtime and evidence

External run under VERUS_SKILL_RUN_ROOT/skillopt-verusage/executive-pilot-*;
validation_contract.json, review.json, run.log, progress.json, provider_calls.jsonl,
full_traces/, summary.json and executive_summary.json. Actual command/PID recorded
in ENTRY.md. Two-worker actor bound about two hours plus provider drain/export;
not a completion guarantee. bash_exec/artifact APIs are unavailable in this
environment: use exec_command plus hashes and canonical memory, without claiming
evidence-graph registration. Baselines/raw/legacy/sealed data stay read-only.

Next on completion: inspect all six paired traces, classify supported/refuted/
inconclusive at development scope, then decide whether broader validation is
justified. Do not infer causal card benefit from read counts.

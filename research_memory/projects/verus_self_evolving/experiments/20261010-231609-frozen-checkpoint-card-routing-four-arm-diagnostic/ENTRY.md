# Frozen checkpoint card routing four arm diagnostic

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-10-10T23:16:09`
- dataset/split: four already-analyzed validation cases, auxiliary/dev only.
- baseline: frozen repaired-78 bank, original Executive, corrected shared TASK.
- variant: none/exposed/index/query, four matched cells per checkpoint,16 total.
- metrics: solved, timeout, settled input/output/cost, applicable exposure, edits.
- leakage controls: no final proof or old conversation; no sealed-test access.
- stop condition: provider invalidity, changed hashes, preflight failure.
- model/runtime: DeepSeek V4 Pro/max,600s/actor, workers2, cost record-only.
- research type: bounded mechanism diagnostic, not independent efficacy test.
- objective: distinguish coverage gaps, failed discovery and failed application.

Full hypothesis, factor, comparator and abandonment contract: [PLAN.md](PLAN.md).

## Commands

```bash
# Set VERUS_SKILL_RUN_ROOT from the ignored machine-local context first.
export PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt
python -m pytest tests/test_card_routing_diagnostic.py tests/test_card_revision_validation_driver.py -q
# Prepare flags/config and hashes are preserved in the external contract.
python scripts/card_routing_diagnostic.py --output "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/card-routing-diagnostic-20261010-231609"
python scripts/report_card_routing_diagnostic.py "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/card-routing-diagnostic-20261010-231609"
```

## Outputs

- run directory: `VERUS_SKILL_RUN_ROOT/skillopt-verusage/card-routing-diagnostic-20261010-231609/`
- launch receipt: `START_RECEIPT.json`; supervisor PID199679.
- launched at:2026-10-11T04:20:49Z (2026-10-10 local).
- logs/current progress: `run.log`, `progress.json`.
- frozen contract: `contract.json`; SHA256
  `1031329472cc8b3804a851c6aae36e07db1cc7bfd25030d23b6495145f4afcf8`.
- case preflight: `checkpoints/<id>/preflight.json`.
- final outputs (prospective): `summary.json`, `statistics.json`, `REPORT.md`,
  `completion.json`, `full_traces/`, settled `provider_calls.jsonl`.

## Results

Completed16/16 with valid provider evidence; none/exposed/index3/4 successes each,
query2/4; timeouts1/1/1/2. Total estimatedUSD1.621275. Zero search-tool calls;
only the failed a23 query episode read cards (six, including006/058). All frozen
hashes unchanged, bridge drained, automatic report/full traces written.
Completed outcome and bounded all-four-a23 trace review: [RESULTS.md](RESULTS.md).
This result supersedes the launch-time progress below.

Status: **partial, live execution started**. Four checkpoints independently fail
Verus and pass the proof-only comparison as required.14 local tests pass,
including standalone query CLI, pagination, hash rejection, no-reference
checkpoint continuation, fail-closed scheduling/drain and reporting denominators.
Initial prepare failed before output creation because run-root env was unset;
setting the explicit safe root corrected it; no provider call was made by that
failed prepare. No inference retry occurred.

Both first actors were active and five completed real provider calls observed,
all identifying `deepseek-v4-pro` with saved public payloads. Neither supplied a
reference proof; continuation hashes match. First case now completes4/4 cells,
all solved; second case is running. No aggregate efficacy result yet.

Applicability review: filtered sequence case gets001 (installed reverse filter
containment lemma); failed quantified rely proof gets006 (missing antecedent)
and058 (instantiate the exact entailment implication). These are advice, not
complete repairs. Always-conjunction and pod-preservation cases have no confirmed
exact match at the selected initial state; their exposed arm has identical
information to none, explicitly a negative control. Broad-topic advice is not
promoted to a supposedly correct card merely to fill this arm.

## Interpretation

Completed diagnostic is negative/inconclusive for improvement; query adoption
was zero, so search quality remains untested. a23 found relevant cards but applied
058 with the wrong surface form and timed out; direct exposure passed190.6s,
none310.8s, index142.5s without full-card reads. No causal claim from one attempt.
Active query retains the same index; any contrast is
about adding optional search access, not index shortening. One attempt per cell,
purpose selection and unequal advice exposure forbid generalized causal claims.
Exposed advice in SKILL.md is not a `card_read` event. Reads/searches do not prove
correct use; manual audit must inspect edit, diagnostic and acceptance sequence.
The full trace is a fresh same-code continuation, not a historical chat replay.
No graph API was available; evidence is hashes, contracts and canonical memory.

## Next Action

Detached execution/reporting complete; bounded a23 review complete. Next proposal:
separate index-replacement query test and concrete exact-term058 application test,
not a combined intervention or automatic full-validation scale-up. No new paid
calls or method implementation in this status check. Separate autoresearch untouched.
Raw datasets, sealed test and previous outputs remain unchanged; all new full
execution outputs are external.

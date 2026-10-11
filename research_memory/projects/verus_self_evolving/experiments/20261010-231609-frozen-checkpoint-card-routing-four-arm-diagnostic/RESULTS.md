# Completed checkpoint diagnostic and bounded trace review

Parent: PLAN.md and frozen external contract. Auxiliary/dev, not independent test.
Outcome:16/16 completed,16 provider-valid,11 solved,5 ordinary600s timeouts.
Run+report exit0; bridge drained; frozen input hashes unchanged at close and
rechecked2026-10-11. All16 public-provider transcript captures complete according
to exporter; hidden/private reasoning is neither available nor reconstructed.
No unmetered/unknown-cost requests. Recorded estimated total USD1.621274688.
Execution04:20:49–04:57:42UTC, approximately36m53s including bridge settlement.

## Aggregate outcome

| Arm | Success | Timeout | All-attempt input | All-attempt output | Estimated USD |
|---|---:|---:|---:|---:|---:|
| Executive only, no cards |3/4|1|6433132|80769|0.367015|
| Pre-reviewed advice exposed |3/4|1|3961564|88965|0.329348|
| Original short index |3/4|1|8051672|76020|0.412153|
| Same index plus optional query |2/4|2|8049378|121120|0.512758|

Input tokens are cumulative request usage, including cache hits/repeated context,
not a single prompt's length. These totals include timeouts. Success-only and
same-case joint-success usage remain separately available in statistics.json.
Do not compare unequal successful subsets as if they establish efficiency gains.

| Case | None seconds | Exposed seconds | Index seconds | Query seconds |
|---|---:|---:|---:|---:|
|62ff filtered containment|26.8 pass|41.5 pass|64.9 pass|49.2 pass|
|a23 quantified rely equivalence|310.8 pass|190.6 pass|142.5 pass|600.4 timeout|
|599 always conjunction|70.7 pass|116.3 pass|91.7 pass|79.4 pass|
|3f17 pod preservation|600.4 timeout|600.5 timeout|600.4 timeout|600.4 timeout|

The two no-confirmed-match exposed arms intentionally have the same information
as none; their differing paths/timing also demonstrate single-attempt variation.

## Query adoption versus card application

Inspection scope/rubric: quantitative accounting and completed command payloads
for all16 episodes; qualitative comparison of all four a23 continuations (the
only between-arm solved-rate disagreement). Review checks actual tool invocation,
returned full cards, edit text, verifier response, time and final acceptance.
Agent self-reports alone do not establish correct application or causality.

No actor invoked card_query.py. The query-condition4 cells emitted zero search
payloads. The old-index4 cells emitted zero card_read payloads. Query availability
was NOT meaningfully exercised, so the search/ranking algorithm is untested here.
The failing a23 query cell did use the old ID reader:058,077,029,070,006,025.
The other15 episodes emitted no card_read payload. Exposed advice is supplied in
SKILL.md and must not be miscounted as absent exposure merely because read_calls=0.

### a23: retrieved applicable advice, but incomplete/misapplied repair

Relative to query actor start04:24:54UTC:

- About171.5s: reads058, then077/029/070/006/025 (six return payloads within~2.5s;
  this is not a measurement of all reasoning time attributable to the cards).
- About218s: first candidate-proof repair, after scratch syntax experiments.
  Correctly switches quantified proof implication to `implies` per006. The
  next verifier run still fails; that advice addresses only one component.
- About309.5s: item42 says it is applying058. Actual item43 patch instead adds
  unfolded Boolean implication assertions, not the exact temporal implication
  satisfaction term matching `entails`' quantifier trigger. In one helper it also
  jumps directly to a suffix instead of establishing the outer `always` premise.
- Remaining time: repeated diagnostics/SMT and syntax investigations. Final
  candidate still has Boolean implications and unguarded directional helper calls;
  the actor times out without full verification.

Successful none/exposed/index candidates instantiate the exact term, e.g.
`assert(spec.implies(always(lift_state(vrs_rely(other_id)))).satisfied_by(ex));`,
and guard directional helper calls with ghost `if` branches. Exposed closes at
190.6s versus none310.8s, but index closes142.5s without reading a full card.
Thus one positive exposed example exists, while finding the reviewed cards is
plainly insufficient for success. Card058's abstract wording may permit an
incorrect surface-form translation; this is an interpretation/hypothesis, not a
proved causal attribution to the wording. The agent also spent substantial time
before any card read. Do not blame all extra time on reader latency or conclude
that query caused the failure: query was never called, and there is only one run.

Evidence: external episodes/routing_query--a23a4969155913255f76/
agent_events.jsonl, codex_events.raw.jsonl, workspace/candidate.rs, saved snapshots;
matched none/exposed/index episode files and stitched full_traces/.
Key query items16–21(reads),22/33(correct006 intention),34/35(first candidate edit
and check),42/43/44(058 claim, actual patch and failed check),45–70(later detour).

## Claim update and next route

No success-rate improvement established. Optional tool addition alone did not
elicit any active searches. The observed failure supports investigating exact
term/application guidance as well as discovery, not merely adding more retrieval.
The hard pod case fails in all conditions and is not a retrieval-only diagnosis.
One attempt/cell, selected validation cases, partial applicability labels and
fresh same-code conversations limit generalization. This is not an augmentation
efficacy test and must not replace the prior full-validation results.

Next route: propose a separate bounded experiment replacing (not supplementing)
the flat index with a short optional query entry, and independently test058 with
a concrete exact-term example. Keep those as separate factors, preserve the old
bank, and do not force retrieval or start new paid/full-validation runs from this
status-report request. Current work is read-only inspection plus canonical memory.

External evidence SHA256:

- summary.json:64c3aae3a1dc5caaa5efb27c4abff72d2707870f0c7b32718928445f5d47922a
- statistics.json:c4a74ad5600311b1025959f21dfb0da07691b62b560cf87c4ba61d3549c1ab11
- REPORT.md:1c4e25927f26d66bf0abe1f9036e3b5768e9c29bfca0b285babf97130e6e4740
- completion.json:6ce4bb21ee3715ea7e2488316994bc180e49b1abcf1340e150704e1593073ce4

Raw/sealed inputs, prior execution artifacts and separate autoresearch unchanged.

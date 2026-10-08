# Helper-inclusive proof-progress proposal

## Authority and status

After the voice clarification that independent helpers are absent from the main
curve, the user said to continue. This turn continued the method explanation and
performed read-only code/source checks. It did not authorize or implement a new
metric, helper pruning, a39-task rerun, checkpoint selection or paid experiments.
Three filled checkpoints per task and native SkillOpt card generation remain
confirmed requirements. The helper-inclusive scope below is a proposal for review.

## Established implementation scope (parsed)

`skillopt-verusage/src/skillopt_verusage/campaign_evidence.py:94` accepts one
target function and occurrence. It calls target-only greedy pruning, then obtains
one `reference_body` and compares each target body with that reference.
`src/verus_self_evolve/proof_progress.py:376` attempts deletions only within that
target body. Independently declared helper bodies are neither pruned nor included
in the main overlap denominator. A helper invocation inside the target can match
a reference line; this does not measure the helper's own proof progress.
Complete-candidate Verus/Lynette checks and reported verified-function counts are
available, but those counts do not enter the main line-overlap curve.

## Read-only diagnostic confirmation (computed, not a new main result)

Parent evidence: `a3c9af1afebbd8d5fe93`, original calls15-18, report/trace paths
bound through the existing reviewed report's `report_provenance.json`.
The unchanged target overlaps1/23 at all four calls. Using each helper's
**unpruned original final body**, the existing line-overlap function gives:

| Call | `lemma_CKeyKV_is_marshalable` | `lemma_u64_ser_len` |
|---|---:|---:|
|15|11/13|3/4|
|16|11/13|4/4|
|17|13/13|4/4|
|18|13/13|4/4|

Both helpers are new relative to the original input declarations. These counts
are diagnostic evidence of target-only measurement blindness, not a new
verifier-pruned aggregate curve. The prior case review also observes reported
errors3 to1 and verified functions2 to4. No source/code file was changed or
verifier/provider call run for this continuation.

## Proposed reference scope (hypothesis, not frozen)

Use the target's proof plus newly added or modified helper proofs actually needed
by the final target, including transitive helper dependencies. Do not count all
functions in the file, unchanged library code or unrelated temporary probes.
Determining actual dependencies needs scope/name disambiguation and a verification
check; a naive text search must not be labeled a complete dependency resolver.

Prune eligible proof content across this reference scope with full-candidate
Verus and Lynette gates. Keep a fixed denominator from the resulting final
reference, rather than adding helpers dynamically to the denominator during the
trace. Compare normalized lines within their own function identities and sum
the matched/total lines; do not let common braces or identical lines in another
function satisfy the wrong function's reference. Keep component curves for the
target and individual helpers alongside the combined diagnostic curve.

Preserve explicit unknown coverage for target-absent probes and parse failures.
A reference helper not yet created is distinct from a parser failure. Helper
success, aggregate overlap1.0 or increased verified-function count alone must
not become proof of complete target verification.

The existing target-only statistics remain valid under their labeled metric;
their plateau counts must not be presented as whole-task stagnation counts.
Expanded scope may repartition platforms and change the availability of three
platform starts. Text overlap remains sensitive to casts/rewrites and misses
learning not retained in the final code even after helpers are included.

## Review question and validation path

Confirm the reference scope: target proof plus actually needed new/modified
helper proofs. Once confirmed and implemented, first verify on the productive
flat, off-target probe, executable target, duplicate-name and short-trace cases;
then rerun the train-only statistics with old reports preserved. Test fixed
denominators, function-local line matching, safety preservation and explicit
unknown states. Do not precommit that every productive flat will become a rise
after pruning, or that helper inclusion solves checkpoint shortage. Continue
labeling the expensive unfinished pruning case separately.

## Evidence and safety

Scientific execution/graph interfaces are unavailable in this session. Ordinary
local read-only checks and this canonical note are the fallback; no science graph
nodes are claimed. Inputs and outputs remain as bound in `ENTRY.md`. No raw or
sealed data, original traces, meeting transcripts or provider ledgers were
written, and no production code changed. No new generated run directory.

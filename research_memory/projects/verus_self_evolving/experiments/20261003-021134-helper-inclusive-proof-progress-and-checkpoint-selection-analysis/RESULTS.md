# Helper-inclusive progress repair: reviewed results

## Evidence and scope

All39 successful training originals are accounted for, with368 recorded verifier
calls. No held-out source, provider request, hint fork or card update was used.
Ten tasks have25 new/changed local proof-helper components in the final compiler
dependency closure. Eleven changed proof functions outside that closure are
excluded from the final-path denominator, but preserved as exploratory evidence.
Compiler-resolved VIR references are a conservative static scope, not a proof
that every included helper is logically necessary. Unchanged libraries are excluded.

The denominator is fixed per final reference; lines match only within their own
function. Missing new helpers are zero, missing targets or ambiguous identities
are unknown. Both combined and target-only curves use the same new reference.
Text coverage is not semantic progress, and includes executable scaffold where
the target is an execution function. Even a verified intermediate can have less
than100% overlap with a later final reference.

## Paired statistics:38 primary tasks

One expensive target reference remains separately labeled verified-unpruned,
as in the parent analysis. It is not included in the primary distributions.
Platforms below are strictly before first observed full-candidate verification;
regressions cover the full trace. No minimum token-span threshold is imposed.

|Metric|Target only, same reference|Target + related helpers|
|---|---:|---:|
|Coverage-only: tasks with0 platforms|18|19|
|Coverage-only: tasks with1-2 platforms|17|15|
|Coverage-only: tasks with at least3 platforms|3|4|
|Coverage-only: total platform spans|32|37|
|Coverage-only: median output tokens per span|1,875.5|1,871|
|Coverage-only: maximum output-token span|95,414|95,414|
|Coverage-only: output tokens inside spans|286,293|239,614|
|State-aware: tasks with0 platforms|21|21|
|State-aware: tasks with1-2 platforms|11|12|
|State-aware: tasks with at least3 platforms|6|5|
|State-aware: total spans|38|38|
|State-aware: median output tokens per span|2,223|2,057.5|
|State-aware: output tokens inside spans|235,729|208,810|

Coverage-only requires equal overlap; state-aware also requires equal nonpassing
verification tier. Adding helper progress can both break old long spans and
create shorter new ones, so total span counts need not fall. The46,679-token
coverage-only reduction is reclassification of observed intervals, not saved or
wasted tokens. Sparse verifier sampling also limits interpretation.

There are40 primary regression flags:4 overlap drops and38 tier drops, with2
overlapping,39 before first verification. Tier0 combines compiler failure and
unparsed diagnostics; these are not all semantic backtracks. The supplement has
3 additional flags, so the full39-task total is43.

Across4 tasks,13 strictly pre-pass transitions have unchanged target overlap but
increased combined overlap. Four additional such transitions end at the first
verification, and2 occur after it:19 across7 tasks in the full-trace inventory.
Do not present all19 as pre-pass stagnation corrections. Seven primary flat
combined-overlap transitions still have fewer reported errors, across5 tasks;
helper inclusion therefore does not solve the semantic-progress problem.

## Candidate availability, not a frozen selector

Only13/39 tasks have at least3 distinct verifier-call candidates when combining
coverage-platform starts, regression-before/after and repeated literal diagnostic
starts. Literal stderr matching is not semantic obligation tracking.
All39 have at least3 presolution context boundaries; even excluding the first
passing code hash, the minimum is5 boundaries, but only23/39 have3 distinct code
states. Reusing the same code at different context prefixes is therefore necessary
for some short traces. These are availability checks, not evidence of three
valuable interventions, preservation-safe replay, or actual selected checkpoints.

## Validation and artifacts

Scoped tests:110 passed,13 subtests passed. New1313 deletion trials accepted168
line/block units, removing183 lines. Every accepted unit passed full Verus and
Lynette against the unchanged original; no new command timed out. These are new
trials only, not the parent's2077 reused target trials. All39 latest-parser scopes
and368 curve values reproduce from exact snapshots. A post-first-pass platform
was excluded consistently from paired summary counts; it remains visible in the
full trace reports. Two macro/external-body parser failures were recovered in a
separate run, with failed outputs retained.

Reviewed external artifact root:
`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/train39-helper-reviewed-20261003-EGEcwN/`

Files: `STATISTICS.md`, `task_statistics.csv`, `platforms.csv`, `regressions.csv`,
`component_curves.csv`, `checkpoint_candidate_inventory.csv`, `summary.json`,
`report_provenance.json`, `all_curves.png`, and39 individual curves. Two earlier
local consolidations are superseded by this reviewed root, not deleted.
Raw sources, sealed splits, original snapshot chains and provider ledgers remain
unchanged. No learned-knowledge utility or causal hint benefit is established.

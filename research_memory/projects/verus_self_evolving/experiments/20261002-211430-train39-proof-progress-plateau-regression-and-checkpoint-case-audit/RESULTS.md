# Initial checkpoint investigation: results and boundaries

## Result

All39 successful originals now have progress curves. Primary statistics use38
fresh verifier/preservation-gated greedy-pruned references. One expensive
controller lemma has a fresh verified original final as a separately labeled
unpruned reference; its pruning is incomplete. The one unsolved train40 source
has no verified reference and is explicitly outside these progress statistics.

The user requires three checkpoints per task, including fallback fill. This
analysis does not select checkpoints, set a length threshold, generate hints,
run forks, extract cards or evaluate downstream utility.

## Definitions

- Progress is multiset overlap of normalized lines in the current target body
  with its final reference body. It is not semantic proof completion. Structural
  lines and unchanged executable code can contribute. Helper bodies are outside
  the target measurement, although the complete candidate is verified.
- Pruning greedily attempts deleting newly added/replaced target-body lines and
  blocks. Accepted deletions pass Verus and Lynette. This is not a proof of
  globally minimal code; failed or timed-out deletions are not accepted.
- A coverage-only platform is a maximal consecutive equal-overlap span between
  recorded verifier calls, ending before the first observed target pass and
  having positive recorded output-token cost. Verification-tier changes do not
  split it. No minimum token threshold defines a "long" platform yet.
- A state-aware platform additionally requires the same nonpassing verifier
  tier at both endpoints. This can split a single visual flat line into several
  spans and omit tier-changing links. Neither definition establishes stagnation.
- Token length is the difference in cumulative provider-reported output tokens
  aligned to endpoint tool calls, including reasoning when included in that
  usage field. It is not the number of tokens in the proof code or verifier log.
- A regression flag is a decrease in line overlap or verification tier between
  adjacent target-present states. Counts below cover the full trace unless
  explicitly restricted. Tier0 includes compilation failure or unparsed output.
- Missing targets in isolated probes have unknown coverage, never artificial
  zero. Probe success does not count as target success. Four such calls occur.
- Curve markers are recorded verifier calls. Connecting lines are visual guides,
  not observations of continuous progress inside the intervening interval.

## Primary statistics:38 pruned-reference tasks

| Platforms before first target pass | Coverage only: tasks | Coverage plus tier: tasks |
|---|---:|---:|
|0|18|21|
|1|15|9|
|2|2|2|
|3|1|3|
|4|1|1|
|5|0|1|
|6|1|0|
|7|0|1|
|At least three|3|6|

Thus35/38 lack three independent coverage-only platforms;32/38 lack three
state-aware platforms. Zero observed platforms does not imply zero difficulty:
some traces have too few presolution verifier samples to observe a flat pair.

| Output-token span statistic | Coverage only | Coverage plus tier |
|---|---:|---:|
|Number of spans|32|38|
|Minimum|107|107|
|Median|1,875.5|2,223|
|Maximum|95,414|95,414|
|Sum across spans|286,293|235,729|

These sums are descriptive spans, not wasted tokens or demonstrated recoverable
savings. State-aware segmentation omits some tier-changing flat intervals.

Regression count distribution across tasks:0:15,1:15,2:2,3:4,4:1,5:1.
There are40 flagged transitions:4 overlap drops,38 tier drops, with two flags
overlapping.23/38 tasks have at least one flag.39 transitions are before the
first observed target pass; one is after an earlier pass. Whole-trace counts
must not silently define a presolution checkpoint pool.

Across the full primary traces,12 transitions in seven tasks have flat overlap
and fewer reported verification errors. Seven of those transitions are strictly
before first pass. Reported error counts are not a complete enumeration of
verification obligations; source/diagnostic review is necessary. Cases include
verified helper progress that the target-body overlap misses.

## Supplemental task, not pooled with the primary statistics

Controller target `lemma_from_after_receive_ok_resp_to_send_delete_pod_req`
(`67a6f714626f9f53eaff`) has26 recorded calls and109,853 output tokens. Under
its unpruned reference it has two coverage-only platforms and four state-aware
platforms, the latter spanning318,14,450,962 and1,165 output tokens. It has
three tier-drop flags and no overlap-drop flags. These are supplemental measures
with a different reference, not an extra fully pruned sample.

The original proof freshly verifies in approximately50 seconds, exceeding the
first batch's30-second limit. A120-second pruning retry then recorded three
individual deletion timeouts; it was terminated for this bounded initial audit,
with all logs preserved. Timeout is not proof invalidity. The separately labeled
unpruned supplement freshly passes Verus and Lynette. Completing this one
expensive pruning pass remains outstanding if an all-pruned comparison is needed.

## Verification and safety

- 39 source diff/snapshot chains, recorded event hashes and original final hashes
  checked; all368 calls have exact snapshots. Current target extraction was
  checked against each reported coverage value, with four explicit probe gaps.
- All39 reference files have fresh passing Verus and Lynette logs. The38 primary
  reports include2,077 pruning verifier trials, not2,077 accepted deletions.
- Original source ledger and fixed training-manifest hashes remain unchanged.
  No held-out or sealed data, no paid provider call and no original-file write.
- Scoped tests:99 passed,13 subtests passed. Parser fixes cover executable
  targets, duplicate-name occurrences, contract blocks and nullable coverage.
- Overview and representative individual figures were rendered and visually
  inspected. External output files include exact provenance and all per-task
  counts/spans, including the separately labeled supplemental row.

## Artifact pointers

All generated outputs remain below `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/`.
Reviewed report: `train39-progress-reviewed-20261002-YeOZGq/`, containing
`STATISTICS.md`, `task_statistics.csv`, `platforms.csv`, `regressions.csv`,
`summary.json`, `report_provenance.json`, `all_curves.png` and39 individual PNGs.
Original input/report bindings are in the batch manifests listed in `ENTRY.md`.

Case analysis and the evidence-bounded proposal are in [CASE_STUDIES.md](CASE_STUDIES.md).
No causal claim about intervention usefulness or learned-skill quality follows
from these retrospective statistics. User review precedes any selector freeze.

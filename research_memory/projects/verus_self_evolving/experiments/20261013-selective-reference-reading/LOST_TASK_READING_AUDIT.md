# Reading audit of tasks lost relative to the flat baseline

## Summary

Audit of the selected final attempts, not the superseded interrupted attempts.
All three losing R2 episodes read reference bodies. None fits the proposed
explanation that neither arm read a card/reference body. This does not establish
that reading caused the loss: retrieval is endogenous to the agent's progress,
and the runs differ in main-skill indexes even when no body is read.

| Task | Flat baseline A | Losing R2 episode | Supported interpretation |
|---|---|---|---|
| `keys_in_index_range_agree` | No observed card-body read; actor finishes in288.4s. | R2-B reads two full references; actor times out, but both checks had already passed. | A termination-budget boundary case, not an unproved final artifact. Reading-induced harm is not established. |
| `always_distributed_by_and` | No observed card-body read; actor finishes in195.1s. | R2-C reads two directories and two reference bodies; final proof fails at timeout. | Difficulty precedes retrieval. References were consulted during recovery but did not resolve it in time. |
| `unpack_conditions_from_spec` | Reads cards006/015/060; cites060 and applies pointwise execution equality; finishes in291.7s. | R2-C reads card056 as a single-rule reference and one other directory; explicitly announces using the reference's strategy, then times out. | Different retrieved content and observable strategy-use evidence, but no controlled evidence that the reference caused failure. |

“No observed body read” is based on inspecting completed raw commands as well
as retrieval audits. All six runs read `SKILL.md`, which contains instructions
and an index. Reading `card_read.py` itself is reading the helper implementation,
not a card. C-unpack's `ls references/` is a listing, not body exposure.

## 1. R2-B: keys_in_index_range_agree

Reader exposures: `universal-instantiation-concrete` (cards037/058/076) and
`opaque-spec-function-facts` (cards019/021/053), totaling11,422 body bytes.
The host records both at approximately483.2s, before the first proof patch.
The earlier commands already investigate `reveal` and closed specifications;
post-read reveal/quantifier work therefore cannot uniquely establish adoption.

Important correction to the shorthand “lost/unsolved”:

- At568.9s, Verus reports `1 verified, 0 errors` on an earlier proof version.
- At596.0s, Verus again passes on the final candidate.
- At598.5s, Lynette returns `EXIT: 0` on that same candidate.
- The latter two events have the same candidate SHA-256 as the final workspace:
  `15521b541ff9a4d5b8b21ea4ea9fcca43b8bbea976cf97106c06013f8bbd95c5`.
- The actor does not terminate before600s. The result records
  `proof_solved=true`, `safety_passed=true`, `timed_out=true`,
  `within_budget=false`; frozen main scoring therefore excludes it.

These are host event-recording offsets from `result.started_at`, deduplicated by
item ID, not claimed model-compute or isolated tool latency measurements.
The final provider request clarifies what happened after both checks:
Lynette completes at03:17:18.095UTC (598.514s); another model request starts
at03:17:18.167UTC (598.585s). The actor is terminated at03:17:19.937UTC
(600.355s). The provider response arrives at03:17:20.950UTC (601.368s),
requesting `exec_command` with `sed -n 100,215p candidate.rs`, i.e. another
source inspection, not a proof edit or final summary. This late call is preserved
in provider capture but never appears as an executed actor command. Therefore
the actor was awaiting the next model response when its deadline expired;
it did not spend a long post-success interval doing more proof work.
Evidence: request20413128100547039e5acd2f9c94f29b in the v2 provider ledger
and its `provider_capture/.../response.txt` completed-response tool-call item.
This is evidence of a valid proof and two successful checks before the actor
deadline, unlike a post-timeout-only host validation pass. It does not authorize
changing the frozen score. A separately defined time-to-valid-proof endpoint
could expose this case, but should be audited consistently across all arms.

## 2. R2-C: always_distributed_by_and

The agent attempts and fails proof patches before reading any reference body.
It receives missing-antecedent warnings and incorrectly states that `implies`
is unavailable (raw line44). That is an agent claim, not a fact about this
Verus version, and it occurs before the first reference read.

At approximately299.4s it opens the compound-stability directory (no body)
and reads `temporal-entailment-pointwise-lifting` (card056). Its next public
message attributes a suggested approach to the reference, then it performs
small implication/quantifier experiments. At569.9s it opens the quantified
antecedent directory and at572.1s reads the full body, covering
cards006/023/069/074. No later proof patch is recorded before timeout; the final
candidate still fails verification. This is late retrieval with no successful
rescue, not evidence that an initially sound proof was derailed by reading.

Baseline A recovers from its own parsing and antecedent errors without reading
card bodies, consults `vstd`, and produces a verified proof using the proper
quantified proof implication form. That different trajectory can reflect
sampling, the different initial index, retrieval choices, or their interaction.

## 3. R2-C: unpack_conditions_from_spec

Baseline A reads006/015/060 before its first patch. Its first verification
leaves a `suffix(0)` equality error; the next public message explicitly cites
card060. The patch and final source implement triggered pointwise equality
followed by `execution_equality`, and subsequent Verus/Lynette checks pass.
This supports observed use of card060, not a counterfactual efficacy claim.

R2-C reads card056 via `temporal-entailment-pointwise-lifting` at approximately
184.8s and opens the compound-stability directory without reading its rules.
Its public message explicitly proposes using the pointwise-lifting strategy
from the reference, followed by a proof patch. Later it struggles to instantiate
premises, explores SMT/trigger logs, and adds `test_inst` diagnostic helpers.
No further card/reference bodies are observed. Final verification fails.

Do not simplify this into “C failed because it did not know card060's trick”:
the C candidate also contains pointwise function equality and `execution_equality`.
The missing-antecedent/instantiation issues and long diagnostic detour are visible;
which instruction or retrieval choice caused them is not established.

## Evidence pointers

Paths below are relative to `VERUS_SKILL_RUN_ROOT/skillopt-verusage/`.
Every episode includes `retrieval_audit.json`, `codex_events.raw.jsonl`,
`agent_events.jsonl`, `result.json`, and `workspace/candidate.rs`.

- Baseline episodes under `card-organization-evaluation-20261012-v5/episodes/`:
  `dev_old--33108254990fcf07c1e2`, `dev_old--599792dd13f472f45fa4`,
  `dev_old--9b9f6ccef89db4103c7f`.
- R2 episodes under `selective-reference-evaluation-20261013-v2/episodes/`:
  `dev_old--33108254990fcf07c1e2`, `dev_revised--599792dd13f472f45fa4`,
  `dev_revised--9b9f6ccef89db4103c7f`.
- B-keys raw lines30/32: body reads;45/51: Verus passes;53: Lynette exit0.
- C-and raw lines44/55: pre-read difficulty;57/59: directory/body;
  60: reference-attributed strategy;100/102: late directory/full body.
- A-unpack raw lines28/34/36/38: reads, citation, patch, Verus pass;
  candidate lines129–134 contain the pointwise execution-equality step.
- C-unpack raw lines16/18/19/21: read, directory, strategy statement, patch.
- Scoring: `skillopt-verusage/src/skillopt_verusage/codex_flash_runner.py:411`
  sets `within_budget` from `not timed_out`, rather than first dual-check time.

No paid calls or experiments; no changes to source data, recorded outcomes,
frozen scoring, or presentation tables. This audit separates exposure, observable
application, and causal effect; only the first two can be examined directly here.

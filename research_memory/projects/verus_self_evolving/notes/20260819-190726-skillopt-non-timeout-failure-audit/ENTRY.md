# SkillOpt Non-Timeout Failure Audit

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-19T19:07:26-05:00`
- status: `complete`

## Objective

Explain why the fixed-80 SkillOpt iterations contain ordinary failures in
addition to successes and timeouts, and determine whether those failures came
from missing Lynette access, agent early termination, or harness/task defects.

## Scope And Evidence

The audit was read-only over the completed canonical run:

- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/`
- main Epoch-1 through Epoch-4 training rollouts and main selection gates;
- frozen train and selection metadata under
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-claude-stratified-80-seed20260814/`;
- the current runner, adapter, split precheck, and frozen execution contract;
- two public IR historical Claude records used only to confirm prior harness
  behavior.

Slow-update and repair-only gates were inspected for consistency but are not
included in the headline counts. Held-out test items were not inspected.

## Result

The state space was intentionally not binary. The task prompt tells the actor
to continue until both checks pass **or useful approaches are exhausted**, and
the frozen execution contract explicitly says that a valid unsolved candidate
is an ordinary hard failure. The host independently runs both Verus and
Lynette after every actor termination, including timeouts. `V2_TRACE` denotes
a complete valid actor trace, not a solved proof; `hard=1` alone requires both
independent checks to pass.

Across the four 20-item main selection gates, 55/80 executions solved and
25/80 were hard-unsolved. Of the 25 unsolved executions, 23 timed out and two
terminated normally. Both normal failures were the same IR task,
`cac8c7541d651d3480ff`. The agent invoked Lynette in both runs, the host
independently judged Lynette as passing, Codex returned normally with a
complete `V2_TRACE`, and final Verus failed. The same task was also the sole
normal failure in the S0 baseline.

Across the four 40-item main training rollouts, 101/160 executions solved and
59/160 were hard-unsolved. Forty-five of the unsolved executions timed out and
14 terminated normally. The actor invoked `run_lynette.sh` in all 14 normal
failures, and the host independently ran Lynette afterward. Thirteen of the 14
normal failures came from eight IR tasks containing the stale first line
`extern crate verus_builtin_macros as builtin_macros;`:

- in two Epoch-1 executions the agent repaired the alias, Verus passed, and
  Lynette correctly rejected the executable-code difference;
- in eleven later executions the agent preserved the alias, Lynette passed,
  and the current single-file Verus wrapper failed before proof verification;
- the remaining one normal failure, task `21d08b2dcc7dc2871787`, was a genuine
  early normal termination: Codex returned at 487 seconds with no edit or final
  message, independent Verus remained at one proof error, and Lynette passed.

The fixed train/selection split therefore contains nine tasks that are
structurally unable to satisfy the current joint contract: eight of 40 train
items and one of 20 selection items. All nine are IR tasks. Their frozen source
prechecks have `verified_count=null` and `error_count=null`, but the split
builder accepted every non-timeout, non-passing Verus invocation as
`source_precheck_failed_as_expected`. Historical Claude had verified several
of these tasks, including the persistent selection item, confirming a current
task/toolchain contract mismatch rather than an intrinsically impossible
proof task.

The result schema makes the issue harder to see. When `hard=0` and the actor
did not time out, the runner records an ordinary failure even if the real
cause is Lynette or infrastructure. Its `fail_reason` always takes the final
Verus diagnostic; for the two Verus-pass/Lynette-fail cases it therefore
records `verification results:: 1 verified, 0 errors` as the failure reason.

## Interpretation

Missing Lynette is not the cause. The normal failures are operationally actor
early terminations, but 15 of the 16 main-loop occurrences (13 train plus two
selection) are explained by one harness/task compatibility defect rather than
ordinary proof-search exhaustion. Only one main-training occurrence is a
clean semantic early stop, and its empty final message prevents a stronger
claim about the actor's intent.

The persistent invalid selection item fails at every checkpoint, so removing
it would change the absolute denominator but not the observed paired gate
deltas. The eight invalid training tasks are more consequential: SkillOpt saw
their traces as proof failures, and the Epoch-1 accepted skill learned an
infrastructure/toolchain rule from them. Existing skill-effect conclusions
must therefore retain this training-evidence contamination caveat.

## Decision And Next Action

Do not reinterpret all ordinary failures as semantic agent failures. Before
any new fixed-80 actor run or held-out test:

1. preflight must require a real Verus verification summary and reject
   frontend, crate, macro, dependency, and wrapper failures;
2. the IR alias/toolchain compatibility must be resolved in the host wrapper
   or the affected tasks must be declared harness-invalid without modifying
   benchmark candidates;
3. final outcomes should separate semantic unsolved, safety rejection,
   infrastructure invalidity, timeout, and provider/terminal invalidity;
4. `fail_reason` must report the failing independent judge rather than always
   copying Verus output.

No runner, split, raw result, or historical artifact was modified in this
audit.

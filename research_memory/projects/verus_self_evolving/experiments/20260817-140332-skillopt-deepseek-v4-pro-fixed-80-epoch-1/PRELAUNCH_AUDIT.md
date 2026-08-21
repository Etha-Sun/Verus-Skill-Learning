# Prelaunch audit: SkillOpt DeepSeek V4 Pro fixed-80 epoch 1

## Scope

An independent GPT-5.6 Sol reviewer performed a read-only adversarial audit before
any paid request. It checked the actor and optimizer call graphs, dataset split,
gate schedule, timeout behavior, provider failure handling, resume behavior,
secret exposure, and token/cost accounting.

## Initial verdict

**FAIL / no-go.** The experiment was not launched.

The static actor call graph is correct: `train.py` selects
`CodexDeepSeekAdapter`, which invokes the isolated hands-off Codex CLI runner
using native Responses. It does not use the legacy VeruSAGE rollout pipeline.
The configured actor is `deepseek-v4-pro`; the optimizer is local Codex
`gpt-5.6-sol`.

| severity | finding | launch impact |
|---|---|---|
| blocker | Native Responses incomplete/error states and failed Codex terminals could be scored as ordinary model failures. | Retry/abort semantics and accuracy could be wrong. |
| blocker | Unsolved 1,200-second actor timeouts were retained without retry. | The prior apparent +1 selection result is not robust to timeout noise. |
| blocker | Actor ledgers omitted unknown-usage attempts and could race still-active bridge handlers. | Final USD and token totals could be incomplete. |
| blocker | Optimizer retry attempts were hidden inside one outer ledger row. | Optimizer token/attempt accounting was incomplete. |
| blocker | The documented bridge command omitted the required manifest and model catalog. | The advertised launch command could not run the formal harness. |
| blocker | Optimizer exhaustion could become `skip_no_patches`, and an S1 identical to S0 could reuse the selection cache. | A nominal epoch could finish with 60 rather than 80 actor tasks. |
| high | Existing-run state was not recipe-safe for resume. | A stale run could silently mix configurations. |

## Dataset audit

The frozen split is internally valid for a same-family, task-held-out pilot:

- exactly 40 train / 20 selection / 20 held-out test tasks;
- AC/AL/IR quotas are matched across splits;
- each split contains 25% historical Claude failures;
- no exact task ID or source-hash overlap and no exported reference proofs;
- difficulty-proxy means are close (train 0.503, selection 0.481, test 0.520).

The split is not project-held-out. AC includes highly similar resource-matching
tasks across splits (maximum five-line-shingle Jaccard about 0.96). Results must
therefore be described as task-held-out within the same project families, not as
evidence of project-level transfer. The frozen split was retained; no data or
sealed source was modified.

## Remediation applied before re-review

- Provider status, returned model, usage, Codex return code, and terminal event
  now fail closed. Invalid native Responses attempts become `V0_INVALID`.
- Returned-model validation uses the exact live-observed API value
  `deepseek-v4-pro`. The provider does not expose an internal build suffix.
- Unsolved actor timeouts retry at 1,200, 2,400, then 3,600 seconds. A timeout is
  at most `V1_TRUNCATED`.
- The bridge exposes active request counts; formal closeout waits for zero active
  requests before writing the cost ledger.
- Actor and optimizer ledgers distinguish successful, failed, metered, and
  unknown-usage attempts. Local optimizer cost remains USD 0; its DeepSeek-rate
  number is explicitly counterfactual.
- A formal-epoch validator requires a fresh run root, a distinct S1, exactly
  20/40/20 current actor results, one strict gate decision, no test execution,
  and complete accounting. Any failure exits nonzero and is not a result.
- The launch script creates and validates the bridge manifest/model catalog and
  removes the real DeepSeek key from actor and optimizer subprocess environments.

## Verification before second review

- 50/50 integration unit tests passed, including malformed/incomplete Responses,
  model mismatch, nonzero Codex terminal, timeout escalation, and unknown-usage
  accounting tests.
- `compileall` and shell syntax checks passed.
- Targeted mypy passed with missing third-party import stubs ignored.
- Offline config/dataloader preflight returned exactly 40/20/20.
- No live provider request and no experiment rollout has been started.

## Second-review verdict

**PASS.** The same independent GPT-5.6 Sol reviewer re-read the frozen final
snapshot and found no residual launch blocker. It confirmed closure of every
initial blocker and the exact live-observed `deepseek-v4-pro` model check.

## Live preflight

One isolated train-split task was run before the formal epoch. It solved with
`hard=1`, `V2_TRACE`, `provider_valid=true`, Codex return code 0, one completed
terminal, and no failed/error terminal. All 31 native Responses calls returned
the exact model alias, completed with usage, and had zero provider errors or
unknown costs. Usage was 892,387 input tokens (871,168 cache hit) plus 18,082
output tokens; the off-peak actor cost was USD 0.068972596. The cost ledger was
complete and all preflight processes exited.

The formal epoch was launched only after both the static PASS and live PASS.

# Execution Prompt: SkillOpt With Codex-Flash Actor And GPT-5.6 Sol Optimizer

You are taking over the SkillOpt-on-Verus experiment in
`/zp_vegeta/scratch_sb/ycsun/Verus-Skill-Learning`. Work autonomously until the
authorized stopping condition is reached. Do not silently substitute a
different agent harness.

## Objective

After the currently running DeepSeek-V4-Pro mismatch diagnostic finishes,
execute a fresh SkillOpt experiment with:

- target/actor: DeepSeek-V4-Flash operating through the repository's Codex CLI
  hands-off agent contract;
- optimizer: GPT-5.6 Sol/high through local Codex quota;
- epoch mechanism: 40 training rollouts followed by a 20-task selection gate;
- continuation: run epoch 1 first, and continue one epoch at a time only after
  the candidate passes the preceding selection gate.

The experiment tests SkillOpt under a Codex target harness. It is not another
`autoverus/verusage` or Verus Copilot run.

## Mandatory Repository Context

Before changing code or launching anything, read these files in order:

1. `AGENTS.md` and `.agent-context.local.md`;
2. `research_memory/BOOTSTRAP.md`;
3. `research_memory/CURRENT.md`;
4. `research_memory/INDEX.md`;
5. `research_memory/projects/verus_self_evolving/PROJECT.md`;
6. `research_memory/projects/verus_self_evolving/decisions/20260813-035234-skillopt-codex-harness-alignment/ENTRY.md`;
7. `skill-evolution-pilot/src/skill_evolution_pilot/codex_runner.py`;
8. `src/verus_self_evolve/codex_baseline.py`;
9. `skillopt-verusage/configs/verusage_deepseek_v4_flash_e1.yaml`;
10. `skillopt-verusage/SkillOpt/skillopt/engine/trainer.py` and
    `skillopt-verusage/SkillOpt/skillopt/evaluation/gate.py`.

Treat `skill-evolution-pilot/src/skill_evolution_pilot/codex_runner.py` as the
target-harness implementation reference. Reuse its workspace, event, usage,
hash, and final-judge contracts rather than inventing a second format.

## Non-Negotiable Harness Identity

Every S0, training, candidate-gate, and later accepted-skill rollout must be a
fresh ephemeral `codex exec` session with the same frozen target contract:

- isolated allowlisted workspace;
- immutable `input.rs` and editable `candidate.rs`;
- identical base task prompt and permissions;
- optional exact `SKILL.md`, with its byte hash recorded;
- no previous trajectories, reference proofs, repository history, external
  files, environment secrets, or network tools visible to the actor;
- local `tools/run_verus.sh` and `tools/run_lynette.sh`;
- independent final Verus and Lynette validation after the agent exits;
- raw Codex JSONL events, normalized events, terminal message, wall time,
  provider usage, and final candidate preserved.

Do not use any of the following as the target harness:

- `/zp_vegeta/scratch_sb/ycsun/RL-verus-1129/autoverus/verusage`;
- GitHub Copilot CLI;
- the old Verus Copilot action/repair scaffold;
- direct one-shot DeepSeek patch generation outside Codex;
- the current Pro retrieval proxy.

The external GitHub Copilot BYOK adapter at
`/zp_vegeta/scratch_sb/ycsun/RL-verus-0209/agentic-pipeline/scripts/copilot/byok_adapter.py`
may be read only for protocol ideas. It cannot be reported as the Codex actor.

## Phase 0: Finish And Quarantine The Active Mismatch Run

Monitor, but do not restart or duplicate, these active outputs:

- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-pro-calibration-8-v2-20260813`;
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-pro-retrieval-pilot-20260813/live_gate_v2`.

Wait until every already-launched worker has written a terminal result. Rebuild
the compact calibration and paired-gate summaries from per-task ledgers if the
old coordinator is absent. Record exact calls, cache-hit input, cache-miss
input, output tokens, confirmed cost, uncertain cost, response-integrity
events, solves, and paired transitions. Label the result
`harness_mismatch_diagnostic`; it is not a SkillOpt-aligned result and cannot
seed an effectiveness claim. Do not launch additional Pro tasks.

## Phase 1: Make Codex CLI Run DeepSeek-V4-Flash Correctly

Pin and record the Codex CLI version. The currently observed version is
`codex-cli 0.146.1`, but rediscover it at execution time.

Codex custom model providers currently use the Responses wire protocol, while
the DeepSeek endpoint is Chat-Completions-compatible. Therefore, do not point
Codex directly at DeepSeek and assume it works. Implement or reuse a minimal
local Responses-to-DeepSeek bridge only if required. Keep the bridge surgical
and test it independently. It must:

- authenticate from `DEEPSEEK_API_KEY` without writing or printing the key;
- map the Codex Responses request to wire model `deepseek-v4-flash`;
- preserve system/developer/user content needed by the frozen actor prompt;
- support Codex shell and file-edit tool calls over multiple turns;
- translate streaming tool calls and final text back to valid Responses SSE;
- preserve finish/stop reason and distinguish provider, transport, timeout,
  length, empty-content, and protocol errors;
- record prompt cache-hit, cache-miss, completion, and reasoning usage when the
  provider returns them;
- expose no general network access to the actor workspace;
- use bounded transport retries and never convert a protocol failure into an
  ordinary proof failure.

Use a machine-local Codex profile or command-line config for the custom
provider. Do not commit API keys, personal absolute credentials, or a modified
user-level Codex config. Record the redacted provider configuration and its
hash in the run manifest.

The bridge is not accepted until all of these preflights pass:

1. exact-text response smoke;
2. actor reads `TASK.md` and `SKILL.md` from an isolated fixture;
3. actor invokes a shell wrapper and receives its output;
4. actor edits `candidate.rs` using the Codex edit mechanism;
5. a one-task Verus smoke reaches independent Verus and Lynette judges;
6. normalized events contain request, reasoning/summary where available, tool
   call, tool result, file edit, and terminal usage evidence;
7. no secret match is present in prompts, events, stderr, or manifests;
8. manifest proves actor model `deepseek-v4-flash`, Codex CLI identity, prompt
   hash, skill hash, source hash, and tool hashes;
9. usage and cost calculated from the provider response reconcile with the
   per-call ledger;
10. an intentionally malformed/length-limited provider response is explicitly
    rejected and retried rather than scored as a task failure.

If the provider cannot sustain Codex tool use, stop and report the bridge as a
capability blocker. Do not fall back to VeruSAGE, Copilot CLI, or direct API
generation.

## Phase 2: Add The SkillOpt Codex Target Adapter

Implement the minimum `EnvAdapter` needed to invoke the validated Codex-Flash
runner. Keep Microsoft SkillOpt pinned and unmodified; place integration code
under the existing project adapter package. The adapter must return, per task:

- `hard = 1` only when final Verus and final Lynette both pass and all immutable
  input/safety checks pass;
- a compact optimizer-visible trajectory grounded in normalized Codex events;
- full evidence paths external to the optimizer prompt;
- task id, model, skill hash, candidate hash, fidelity, timeout status, calls,
  tokens, cost, and wall time;
- `V0_INVALID` for harness/provider/protocol corruption, never a silent zero.

Add resume support. Reuse a completed task only when source hash, skill hash,
actor model, Codex version, base prompt hash, bridge hash/config, timeout, and
judge-tool hashes all match. Archive an incomplete attempt before retrying.

Write generated outputs only below `VERUS_SKILL_RUN_ROOT`. Never modify, move,
rename, or commit raw/sealed datasets. Use only the frozen Anvil/IronKV split;
do not evaluate the 40-task test split during this experiment.

Before live rollout, run focused unit/fault-injection tests, full relevant
tests, `compileall`, targeted mypy, and `git diff --check`.

## Frozen Epoch Configuration

Use these settings unless a mechanical provider limit forces a documented
preflight change:

- split: existing leakage-audited 40 train / 20 selection / 40 test split;
- initial skill: `skillopt-verusage/skills/initial.md`;
- seed: 42;
- actor: `deepseek-v4-flash` through the validated Codex harness;
- optimizer: `gpt-5.6-sol`, reasoning effort `high`, local Codex quota;
- train batch: 40 tasks, one full batch per epoch;
- target concurrency: 40 during training and 20 during selection; a worker
  pool larger than the phase task count does not increase effective parallelism;
- reflection minibatch size: 8;
- failure-only reflection: false; analyze both failures and successes;
- merge batch size: 8;
- textual learning rate/edit budget: 4;
- minimum edit budget: 2 with cosine decay;
- skill update mode: patch;
- selection gate: enabled, hard metric, semantic-density bonus disabled;
- selection size: 20;
- test evaluation: disabled;
- meta skill: disabled for epoch 1; do not enable it until an accepted epoch can
  actually supply prior-epoch evidence;
- slow update: keep the upstream epoch-1 placeholder behavior; any later slow
  update must itself be selection-gated;
- actor task timeout: frozen at 1,200 seconds for every compared condition;
- transport/stream idle timeout: at least 600 seconds, with explicit retry;
- target task retry: only for harness/provider invalidity, not to resample an
  ordinary valid proof failure.

Do not impose the old VeruSAGE 20-repair or 512-request semantics on Codex. A
Codex task is one hands-off session bounded by the frozen 1,200-second task
timeout. When that timeout expires, preserve and independently judge the best
candidate, mark `timed_out=true`, and count the valid outcome normally. Retry
only if the harness itself is invalid.

## Exact Workflow

### Initial baseline

Run S0 once on the frozen 20 selection tasks through Codex-Flash. This defines
`current_score` and `best_score`. Do not reuse a VeruSAGE/DeepSeek result as the
Codex baseline.

### Epoch 1

1. Run the current accepted skill on all 40 training tasks through Codex-Flash.
2. Feed compact, evidence-linked trajectories into the native SkillOpt
   reflection/merge/ranking/patch workflow.
3. Run all optimizer stages with GPT-5.6 Sol/high through local Codex quota.
   Do not apply an artificial optimizer completion-token cap. Preserve each
   optimizer call, token report, proposed edits, ranking, rejected edits, and
   final candidate hash.
4. Apply only native SkillOpt-selected edits. Do not manually improve model
   output. Host-side schema, safety, evidence-label, and forbidden-content
   checks may reject a candidate but may not rewrite it.
5. Evaluate the candidate on the exact same frozen 20 selection tasks through
   the exact same Codex-Flash target contract.
6. Invoke the unmodified SkillOpt hard gate. A tie is rejection: the candidate
   passes only when candidate hard score is strictly greater than the current
   accepted score. Independently report paired `0->0`, `0->1`, `1->0`, and
   `1->1` transitions, Lynette failures, timeouts, tokens, wall time, and cost.

### Conditional continuation

- If epoch 1 is rejected or tied: stop immediately, retain S0/current best, and
  do not run epoch 2 or the test split.
- If epoch 1 passes: promote the exact gated candidate and run epoch 2 with the
  same 40-train/20-selection contract.
- Continue one epoch at a time only after the preceding candidate passes.
- Stop at the first rejected/tied gate and retain the best accepted skill.
- Maximum without a new user decision: four total epochs, matching the paper's
  default horizon. Do not run epoch 5 automatically.
- Do not open the 40-task held-out test merely because a selection gate passes.

Never continue based on training score, optimizer confidence, soft score,
offline information gain, or a manually preferred skill.

## Robustness And Failure Semantics

- Empty, malformed, length-limited, interrupted, or protocol-invalid model
  responses are explicit harness events and must be retried at the response or
  task level according to the frozen policy.
- A provider timeout retries the same logical request/session state when safe;
  do not erase the earlier attempt.
- Exhausted harness retries yield `V0_INVALID` and abort the phase. They do not
  enter the SkillOpt score as zero.
- A valid Codex task timeout or a valid unsolved candidate is an ordinary hard
  failure and remains in the score.
- Coordinator interruption must be resume-safe. Never discard completed paid
  results, and never rerun a matching completed task.
- Do not claim a gate result until all 20 paired results pass manifest and
  independent-judge audits.

## Cost And Approval Contract

Maintain one cumulative DeepSeek ledger across the current mismatch closeout,
Codex-Flash preflights, S0, training, and candidate gates. Record per request:

- cache-hit prompt tokens;
- cache-miss prompt tokens;
- completion and reasoning tokens;
- finish reason and response integrity;
- confirmed USD, uncertain USD, and active reservation separately.

Local GPT-5.6 Sol optimizer quota has metered API cost USD 0, but its tokens and
API-equivalent estimate must still be recorded.

The prior standing instruction requires approval before confirmed cumulative
DeepSeek spend exceeds USD 20. This execution order does not authorize hiding
cost in reservations or uncertain exposure. Before the first new live
Codex-Flash batch, reconstruct the cumulative confirmed spend from durable
ledgers and present the projected epoch range. If committed confirmed exposure
would cross USD 20, ask the user for approval before reserving those calls.
Also stop and ask before any additional epoch materially exceeds the approved
envelope. Reservations are not actual spend and must never be reported as such.

## Reporting And Closeout

While running, report at least:

- effective task concurrency and active provider requests;
- completed/total and solved/total for each phase;
- candidate/current paired transitions at the gate;
- confirmed, uncertain, and reserved cost separately;
- invalidity, timeout, truncation, and retry counts.

At each accepted/rejected gate, create a compact English-ASCII research-memory
entry containing objective, frozen contract, exact metrics, caveats, artifact
pointers, decision, and next action. Update `research_memory/CURRENT.md`, run
`python3 research_memory/scripts/mem.py index`, and confirm raw/sealed data
safety. Do not commit raw traces, task workspaces, secrets, token tables, or run
directories.

Make timestamped Git commits at meaningful checkpoints:

1. Codex-Flash bridge and preflight contract;
2. SkillOpt Codex adapter and tests;
3. each completed epoch/gate and research closeout.

Stage only relevant paths, preserve unrelated dirty work, and push the active
branch after each reviewed checkpoint. A commit message must state the real
date/time and what changed.

The final user report must lead with the gate result and include: actor harness
identity, optimizer identity, epoch count, per-epoch 40/20 metrics, paired
transitions, tokens/cost, accepted best-skill hash, stop reason, durable paths,
Git commit/push status, and the explicit caveat that selection-gate success is
not held-out-test evidence.

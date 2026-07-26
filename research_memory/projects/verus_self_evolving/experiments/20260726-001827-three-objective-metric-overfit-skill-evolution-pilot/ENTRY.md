# Three-objective metric-overfit skill evolution pilot

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-26T00:18:27`
- status: `running / token branch`
- dataset/split: `n=4` frozen tasks shared by three isolated objective
  workspaces; three tasks are the prior Codex three-case baseline and the
  fourth is the user-selected IronKV
  `delegation_map_v__impl4__range_consistent_impl`, now labeled
  `hard_solved` after fresh H0 screening.
- baseline: one fresh, high-fidelity Codex H0 trajectory per task under the
  normal prompt and identical harness.
- variants: each objective-specific meta-agent analyzes only its own workspace
  and emits three candidate skills per iteration.
- objectives:
  - token workspace: minimize Expected Tokens to Success using Codex agentic
    trajectories;
  - small-model workspace: maximize verifier-safe small-model performance using
    an API-backed agentic harness;
  - InfoGain workspace: maximize pre/post full-proof teacher-forced IG using
    Codex pre/post summaries and a frozen local scorer.
- leakage controls:
  - clone H0 traces into isolated workspaces;
  - never expose cross-objective metrics or workspaces to a meta-agent;
  - candidate execution agents see only the current task, current skill, and
    allowlisted tools/context;
  - reference proof is evaluator-only;
  - preserve visible messages, tool calls/results, patches, verifier outputs,
    usage, and visibility manifests;
  - record provider-exposed reasoning-token counts without claiming hidden
    chain-of-thought access.
- stop condition: do not launch until the fourth task, API small-model contract,
  full-proof target span, maximum agent iterations, and visibility schema are
  frozen.

## Per-Iteration Accounting

For `n=4`, each meta-agent call both analyzes the previous round and emits the
next three skills:

| workspace | Codex traces/calls | small-model API trajectories | local scoring sequences |
|---|---:|---:|---:|
| token | `3n + 1 = 13` | 0 | 0 |
| small-model | 1 | `3n = 12` | 0 |
| InfoGain | `3n + 1 = 13` | 0 | first round 28; later 24 |
| shared H0, first round only | `n = 4` | 0 | four cacheable baselines included above |

Therefore the first round uses 31 Codex agent invocations, 12 small-model
agentic trajectories, and 28 local teacher-forced sequences. Later rounds use
27, 12, and 24 respectively. A final frozen synthesis adds three Codex
meta-agent calls.

The 12 small-model trajectories are not necessarily 12 HTTP requests. With one
model call per agent step and `max_iters=10`, they require at most 120 API
requests per iteration; both counts must be reported.

The InfoGain accounting assumes one Codex trajectory emits a frozen pre-summary
before tool use and a terminal repair summary after exploration. The local
scorer reuses four no-summary baseline likelihoods and scores 12 pre plus 12
post contexts.

## Outputs

- workflow figure:
  - `figures/three-objective-skill-evolution-loop.mmd`
  - `figures/three-objective-skill-evolution-loop.md`
  - `figures/three-objective-skill-evolution-loop.png`
- reviewed pilot controls:
  - `skill-evolution-pilot/EXPERIMENT_PLAN.md`
  - `skill-evolution-pilot/INFORMATION_CONTRACT.md`
  - `skill-evolution-pilot/DEBUG_GATES.md`
  - `skill-evolution-pilot/TRACKER.md`
- future run root:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/<run_id>/`

## Current Evidence / Caveat

The fresh canonical three-task H0 batch passed 3/3 with complete F3 evidence.
The selected fourth task did not reproduce the expected current-Codex failure:
the standard source and its no-lemma variant both solved. The standard source
is retained as a costly `hard_solved` task; it must not be reported as a
current Codex failure. Both screens are separately costed outside the four
shared H0 calls.

The current Codex baseline harness already provides an ephemeral
`gpt-5.6-sol/high` workspace, JSONL events, final candidate diff, usage summary,
and independent Verus/Lynette validation. It is a useful base, but the evolve
pilot additionally requires allowlisted visibility manifests, explicit payload
completeness, candidate-hash binding at every verifier checkpoint, and secret
redaction.

The historical OpenRouter iterative-refinement script is not suitable as the
new primary harness: it does not provide the required host-controlled
workspace/event schema and may print provider error bodies. The new
OpenRouter-Qwen adapter must accept the credential only through
`OPENROUTER_API_KEY`, sanitize every persisted request/response, and report
actual model-request count separately from trajectory count. OpenRouter
`qwen/qwen3.6-27b` is the primary small-model transport. Local Qwen is permitted
only as a separately labeled fallback arm after a declared no-credit or
bounded provider-availability failure; the results must not be pooled.

## Launch Gates

The token branch is deliberately first because its metric and Codex transport
can be audited before the InfoGain scorer is ready. The executable sequence is:

1. model-free normalized-event and credential-redaction tests;
2. two fresh one-task Codex fidelity runs;
3. OpenRouter provider preflight and one-task Qwen fidelity run;
4. token-ledger recomputation test;
5. six-call token engineering smoke: two H0, one meta-agent, and three
   skill-conditioned solver calls;
6. capped H0-only screen for the fourth task;
7. the full 12-run token candidate matrix.

The smoke is harness evidence, not support for the research claim. The full
round cannot launch if any trace is not fully auditable, a verifier result is
not bound to its code hash, a secret/reference proof leaks, or the fourth task
remains unresolved.

## Infrastructure Evidence (2026-07-26)

The experiment-local implementation now lives below
`skill-evolution-pilot/src/skill_evolution_pilot/` with 27 passing model-free
tests. It preserves raw Codex/OpenRouter fields without payload truncation,
builds a secondary normalized event index, redacts runtime credentials, creates
allowlisted visibility manifests, and records complete candidate snapshots and
diffs at tool/edit boundaries.

Two real Codex fidelity smokes used the prior `stable_pass`
`seq_filter_contains_implies_seq_contains` task. This was a logging test, not
the fourth task and not skill-evolution evidence.

- Smoke 01 solved the task but was correctly rejected as F3 because four
  complete Codex 0.144.5 `todo_list` events were conservatively classified as
  unknown/incomplete. The run is retained.
- After adding a lossless `todo_list` mapping, smoke 02 solved the same task and
  passed F3: 25/25 raw events exactly indexed, six completed command/edit
  boundaries covered by eight full candidate snapshots, complete command
  output/status/exit fields, zero truncation markers or shell-edit suspects,
  unchanged input, and matching independent Verus/Lynette validation.
- Smoke 02 usage was 232,495 input, 203,264 cached input, 1,671 output, and 369
  reasoning-output tokens. It returned no visible reasoning text because the
  harness had not requested a reasoning summary.

A subsequent audit found that the local `gpt-5.6-sol` catalog declares
`supports_reasoning_summaries=true` but defaults to
`default_reasoning_summary="none"`. Smokes 01-02 therefore cannot establish
reasoning unavailability and are not the canonical final configuration.

Smoke 03 explicitly set `model_reasoning_summary="detailed"`,
`model_supports_reasoning_summaries=true`, `hide_agent_reasoning=false`, and
`show_raw_agent_reasoning=true`. It passed F3 and returned four visible
reasoning events containing 186 characters in total, while usage reported 392
reasoning-output tokens. All four events were preserved exactly in raw and
normalized logs. The returned text is a reasoning summary, not the complete
392-token hidden chain-of-thought. Smoke 03 is now the canonical Codex
fidelity configuration.

Unavailable reasoning fields may remain `null`, but the harness must first
request all supported reasoning visibility. Hidden chain-of-thought is not
claimed.

Reviewed run log:

- `skill-evolution-pilot/RUNLOG.md`

## Token Execution Update (2026-07-26)

- Canonical three-task H0: 3/3 F3, 3/3 solved.
- Primary uncached tokens: 25,555 / 71,816 / 32,784.
- Stable-pass H0 repeat variation: mean 27,660, CV 10.8%.
- One-task meta-agent output: exactly three schema-valid skills.
- One-task H0/aggressive/conservative/structural: all F3 and solved; 25,555 /
  20,320 / 15,611 / 28,880 primary uncached tokens.
- Fourth standard source: F3 solved, 410.97 seconds, 79,245 uncached tokens.
- Fourth no-lemma diagnostic: F3 solved, 496.61 seconds, 81,130 uncached
  tokens.
- A full-four meta attempt that used `/tmp` was rejected by the visibility
  gate. A subsequent isolated attempt stalled before tool use and was
  terminated. The next retry passed schema and visibility audits in 327.04
  seconds and emitted `bounded-exploration-gate`, `delta-certificate`, and
  `obligation-graph`.
- The frozen 12-run token matrix is running with concurrency 6 and a
  600-second per-run cap.

The one-task token deltas are engineering evidence only. The first
research-facing comparison remains the frozen 3-skill x 4-task matrix.

## Next Action

Monitor and audit the running frozen token matrix, reconstruct per-run ledgers,
and produce the failure-aware aggregate. In parallel, connect the
tested OpenRouter completion adapter to the host-controlled Qwen repair loop.
The API credential remains process-environment-only; if it is unavailable,
run the already-approved local fallback as a separately labeled arm.

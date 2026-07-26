# Debug and Launch Gates

Status: `DRAFT`

No later gate may run before all earlier required gates pass.

## G0: repository and output safety

Checks:

- external run root exists, is writable, and is outside the repository/data
  root;
- raw inputs open read-only;
- a synthetic run can create the required artifact tree externally;
- repository output contains only control documents;
- no credential-like value appears in tracked or newly created files.

Pass evidence:

- path-validation test;
- generated-output inventory;
- repository diff limited to intended planning/memory files.

Stop:

- output resolves into the repository or raw-data root;
- any input mutation.

## G1: model-free normalized event test

Use fake Codex and OpenAI-compatible responses; do not call a model.

Inject:

- one normal tool call;
- one failed tool call;
- one edit;
- two verifier checkpoints;
- one deliberately incomplete payload in a negative fixture;
- one missing usage field;
- one malformed response;
- one fake credential in every exception path.

Pass:

- event order and call pairing validate;
- verifier records bind to candidate hashes;
- missing usage remains null;
- the negative fixture is rejected from F3;
- fake credential is absent from every artifact and stderr;
- transport adapters produce the same normalized schema.

## G2: Codex independent-workspace fidelity

Configuration:

- model: `gpt-5.6-sol`;
- reasoning effort: `high`;
- ephemeral session;
- workspace-write sandbox;
- ignored user configuration/rules;
- no network or repository history;
- one frozen task, no skill.

Run twice in separate workspaces.

Inspect at these debug nodes:

1. pre-launch workspace inventory and visibility hash;
2. exact stdin prompt hash;
3. Codex lifecycle start/model identity;
4. each command/tool call and completion;
5. each edit or changed candidate hash;
6. each Verus invocation and its candidate hash;
7. each Lynette invocation and its candidate hash;
8. usage-bearing terminal event;
9. final independent Verus/Lynette validation;
10. post-run workspace inventory and redaction scan.

Pass:

- both runs are F3;
- zero JSON parse errors;
- immutable input unchanged;
- every visible tool step is reconstructable;
- every completed command retains complete output/status and exit code;
- every edit has a complete patch plus before/after candidate snapshots;
- a full candidate snapshot exists after every completed edit/tool boundary;
- final validation matches recorded status.
- reasoning text/count is preserved when returned and explicitly null when not
  returned; its absence alone is acceptable.

Stop:

- Codex version/model mismatch;
- missing tool output needed to understand the loop;
- any truncated payload or summary-only edit;
- verifier output not bound to code;
- hidden prior-answer visibility.

## G3: OpenRouter secret and provider preflight

The credential must already exist in `OPENROUTER_API_KEY`. The launch program
must never echo it or accept it on the command line.

Checks:

1. fake credential redaction test passes;
2. one minimal request is made with the requested model;
3. response status and model identity are parsed;
4. usage/finish fields are recorded as available or null;
5. stored request excludes authorization headers;
6. repository and external run scan find no secret/canary.

Classify failures:

| class | action |
|---|---|
| authentication | stop; do not use local fallback as a silent replacement |
| no credit/payment required | record provider unavailable; allow new local-Qwen arm |
| rate limit | bounded retry/backoff, then stop |
| transient server/network | bounded retry, then record and allow new local arm |
| model mismatch | stop |
| malformed response | stop and preserve sanitized diagnostic |

No automatic fallback occurs inside the same run.

## G4: Qwen one-task agentic fidelity

Run one task using the OpenRouter Qwen model through the host-controlled loop.
The model may only request allowlisted operations:

- read visible workspace files;
- replace or patch `candidate.rs`;
- run Verus on `candidate.rs`;
- run Lynette against `input.rs`.

At every iteration inspect:

- sanitized request/response pair;
- request number and finish reason;
- proposed action;
- host-executed action;
- exact edit and candidate hash;
- verifier output and hash;
- per-request/cumulative usage;
- stopping reason.

Pass:

- F3 trace;
- requested/returned model contract passes;
- final independent validation reproduces outcome;
- actual request count equals recorded count.

## G5: token accounting smoke

On one task, run H0 twice and one candidate skill once.

Checks:

- prompt-token difference equals the skill injection under the primary
  accounting source within the declared tolerance;
- cached tokens are not double-counted;
- tool-result re-entry is represented;
- timeouts and failed attempts remain in ETtS;
- no-success condition produces infinite ETtS;
- reasoning-token absence is null.

Pass:

- ledger recomputation from per-request rows equals result totals;
- a second audit program independently reproduces the aggregate.

## G6: token meta-agent and three-skill smoke

Give a fresh Codex meta-agent only the token reflection pack. Validate that it
emits exactly three schema-valid skills. Run all three on the same one-task
smoke.

Inspect:

- meta visibility manifest;
- no cross-objective files;
- negative scope in each skill;
- identical solver configuration except the skill text;
- four-way H0/candidate ledger.

Pass:

- all runs are F3;
- at least two candidates complete normally;
- high/low comparison is mechanically reproducible.

This gate authorizes the full token branch but is not a research result.

## G7: fourth-task freeze

Build a historical Sonnet-failure shortlist using H0-only evidence. Run a
capped Codex screen with the same H0 contract.

Pass:

- exactly one task is selected by a predeclared rule;
- current Codex fails under the frozen budget;
- task/source hashes and screening cost are stored;
- no skill-conditioned run influenced selection.

If no task qualifies, stop and revise `n` or the selection rule explicitly.
Do not choose a task after observing candidate-skill performance.

## G8: full token first round

Run three frozen token skills on four tasks: 12 Codex solver trajectories.

Pass:

- 12/12 result records present;
- every primary-analysis row is F3;
- independent metric audit passes;
- H0 pairing is complete.

Decision:

- reflect once if a valid best/worst mechanism exists;
- otherwise stop the token branch and document why.

## G9: full small-model first round

Prerequisites: G3 and G4 pass.

Run 12 API-Qwen agentic trajectories. Freeze `max_iters` before launch.

Pass:

- all actual HTTP requests are counted;
- API failures are retained;
- no local result is pooled;
- solve rate uses Verus plus Lynette.

If OpenRouter is unavailable under the failure policy, start a new, explicitly
labeled local-Qwen sensitivity run from the same frozen task/skill contract.

## G10: InfoGain contract and scorer

Checks:

- complete proof or exact target span frozen;
- pre summary is emitted before the first tool call;
- post summary is emitted only at terminal state;
- reference proof is evaluator-only;
- baseline score is reproducible;
- context length/truncation policy is frozen;
- local scorer logs token-level target coverage and total score.

Pass:

- four H0 no-summary scores reproduce;
- synthetic helpful/null/adversarial summaries behave as expected enough to
  diagnose scorer direction;
- zero target tokens are silently dropped.

Only then launch the 12 pre/post candidate trajectories and 28 first-round
scoring sequences.

## G11: branch reflection and continuation

For each branch separately:

- audit completeness and leakage;
- recompute primary metric;
- expose best, worst, and all aggregates to its meta-agent;
- validate revised meta-skill and three skills;
- estimate the exact next-round call budget.

One further round requires an explicit go decision. Negative or unstable first
results are valid reasons to stop.

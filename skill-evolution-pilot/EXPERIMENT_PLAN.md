# Three-Objective Skill Evolution Pilot: Experiment Plan

Status: `DRAFT / NOT LAUNCHED`

## 1. Goal and scope

The experiment asks what objective-specialized skills look like when a
meta-agent is deliberately allowed to overfit one metric:

- token skill: reduce the total token cost required to obtain a verifier-safe
  repair;
- small-model skill: improve agentic Qwen3.6-27B verifier-safe solve rate;
- information-gain skill: improve a frozen local model's teacher-forced score
  of a complete reference proof when conditioned on a pre- or post-run terminal
  repair summary.

The same four tasks and the same initial H0 evidence are used across the three
branches, but the branches have separate workspaces, meta-agents, skills,
metrics, and reflection packs. This is three controlled single-objective
experiments, not one scalarized multi-objective optimizer.

The pilot does not claim cross-task generalization. Its purpose is to establish
whether a metric-overfit loop is measurable, controllable, and auditable before
scaling to held-out tasks.

## 2. Frozen claims and anti-claims

### C1: objective-isolated improvement

Under a frozen task set, model, prompt, tool harness, and budget, an
objective-specific meta-agent can emit a skill whose mean designated metric is
better than the matched H0 condition without invalid verifier or safety
outcomes.

Evidence required:

- paired per-task H0 and skill-conditioned runs;
- exact prompt/skill/model/tool hashes;
- complete token or outcome ledger;
- independent final Verus and Lynette validation;
- all attempts, including failures and timeouts.

### C2: auditable strong-to-weak comparison

A visibility-controlled host program can produce comparable high-fidelity
Codex and Qwen agent trajectories: requests, visible responses, tool calls,
tool results, edits, evaluated code state, verifier results, usage, and final
outcomes can be bound to one run manifest.

Evidence required:

- a fresh workspace and visibility manifest for every run;
- a normalized event schema shared by OpenRouter and local-Qwen adapters;
- provider-native raw responses preserved only in the external run root after
  sanitization;
- no silent substitution of model or transport;
- no missing code hash at a verifier checkpoint.

### Explicit non-claims

The pilot must not claim:

- generalization from four evolution tasks;
- token improvement when a run merely fails earlier;
- hidden chain-of-thought recovery;
- equivalence between OpenRouter and local inference;
- InfoGain improvement as proof of live solve-rate improvement;
- skill value when a reference proof or cross-objective result leaked into the
  solver or meta-agent.

## 3. Experimental units

### Tasks

Use `n = 4` frozen repair tasks:

1. the prior stable-pass diagnostic;
2. the prior stable-closest-failure diagnostic;
3. the prior unstable diagnostic;
4. one historical Sonnet failure that current Codex also fails under the
   frozen H0 budget.

The fourth task is not yet identified. A separately budgeted screening run is
required. Screening calls are not part of the four H0 calls and must be
reported separately.

### Models and transports

| role | primary model/transport | fallback | pooling rule |
|---|---|---|---|
| proof solver and meta-agent | Codex `gpt-5.6-sol`, reasoning effort `high` | none | one fixed Codex configuration |
| small-model proof solver | OpenRouter `qwen/qwen3.6-27b` | local Qwen3.6-27B only after a declared provider failure | API and local results are separate arms |
| InfoGain scorer | frozen local Qwen3.6-27B teacher forcing | none during a frozen run | scorer revision creates a new run ID |

An OpenRouter response must report the requested model identity. A different
model, route that cannot be identified, or silent provider substitution is a
failed fidelity check rather than a valid sample.

Qwen solver/inference runs freeze `temperature=0.2` and `top_p=1.0`; the
minimal provider-connectivity preflight uses `temperature=0.0`. Skill/meta
generation is intentionally more exploratory: an API meta-agent would use a
separately frozen initial value of `temperature=0.7`, never the solver
temperature. The primary meta-agent is Codex, whose CLI does not expose a
supported temperature control; it produces three explicitly different skill
roles in one call. Codex stochasticity is handled by matched configuration and
repeated H0 runs rather than an unverified config field.

### Candidate count and iterations

Each objective-specific meta-agent emits exactly three skills per iteration:

- one aggressive skill optimized primarily for the objective;
- one conservative skill that preserves verifier-safe behavior;
- one structurally different exploratory skill.

Three candidates are enough to expose meaningful high/low contrasts while
keeping the first pilot affordable. Start with one full iteration. Approve a
second iteration only if the first has complete logs, valid metric accounting,
and at least two candidates with valid results on at least three of four tasks.

## 4. Metrics

### Token branch primary endpoint

The primary endpoint is Expected Tokens to Success, not tokens per attempt:

```text
ETtS = total counted tokens across all attempts / verifier-safe successes
```

If a condition has zero successes, ETtS is infinite. Also report:

- prompt tokens;
- cached prompt tokens;
- visible output tokens;
- provider-reported reasoning tokens when available;
- tool-result text tokens reintroduced into model context;
- number of agent turns, verifier calls, retries, and timeouts;
- solve rate and wall time.

Provider reasoning tokens that are not exposed are recorded as `null`, never
as zero. The primary paired comparison uses one fixed accounting policy and
the provider-native usage fields. A local tokenizer audit is secondary and
must not silently replace provider accounting.

### Small-model branch primary endpoint

Primary:

```text
verifier-safe solve rate = Verus pass AND Lynette pass
```

Secondary:

- success iteration;
- actual HTTP/model request count;
- prompt, completion, and total tokens;
- wall time and provider cost when returned by the provider;
- verifier-error trajectory.

Twelve agentic trajectories do not mean twelve API requests. With
`max_iters = 10` and one model request per iteration, one round can use up to
120 OpenRouter requests.

### Information-gain branch endpoint

For a complete reference proof `y`, task context `x`, and summary `s`:

```text
IG(s) = log p_score(y | x, s) - log p_score(y | x)
```

Measure both:

- `IG_pre`: summary emitted before any tool call;
- `IG_post`: terminal repair summary emitted after the agent stops.

The score is teacher-forced over a frozen, complete proof target or a
predeclared exact target span. The reference proof is evaluator-only. It is
never visible to the solver or meta-agent. Information gain remains a
secondary offline endpoint.

## 5. Per-round call accounting

Let `n = 4`, three candidate skills, and one meta-agent call per branch.

### Shared H0

The first round begins with four fresh Codex H0 trajectories, one per task.
These are cloned as read-only evidence into the three branch-specific
reflection workspaces.

### Full first round

| branch | Codex proof trajectories | Codex meta calls | Qwen trajectories | local scoring sequences |
|---|---:|---:|---:|---:|
| shared H0 | 4 | 0 | 0 | four cacheable baselines included below |
| token | 12 | 1 | 0 | 0 |
| small-model | 0 | 1 | 12 | 0 |
| InfoGain | 12 | 1 | 0 | 28 |
| total | 28 | 3 | 12 | 28 |

Thus the first round uses 31 Codex invocations in total, of which 28 are proof
trajectories and three are meta-agent calls. It also uses 12 agentic Qwen
trajectories and 28 local scoring sequences.

The 28 first-round InfoGain sequences are four reusable no-summary H0 scores,
12 pre-summary scores, and 12 post-summary scores.

### Later round

With cached H0 evidence, a later round uses:

- token: 12 Codex proof trajectories + one Codex meta call;
- small-model: 12 Qwen trajectories + one Codex meta call;
- InfoGain: 12 Codex proof trajectories + one Codex meta call + 24 scoring
  sequences;
- total: 24 Codex proof trajectories + three Codex meta calls, 12 Qwen
  trajectories, and 24 scoring sequences.

A final frozen synthesis is three additional Codex meta-agent calls, one per
branch.

### Token-first engineering smoke

Before the full round:

1. run one Codex H0 task;
2. repeat the same H0 task in a fresh workspace to audit trace completeness;
3. invoke the token meta-agent once to emit three skills;
4. run the three skills on that one task;
5. invoke one reflection call only if all four solver runs are auditable.

This is six Codex invocations before optional reflection, or seven with it.
It is a harness smoke, not evidence for C1.

## 6. Execution stages and decision gates

### Stage A: static contracts

Deliverables:

- frozen task records and source hashes;
- model, prompt, tool, timeout, and budget contract;
- normalized event schema;
- visibility and secret-redaction contracts;
- metric ledger schema.

Pass:

- every required field has a deterministic producer;
- no credential or reference proof appears in a solver-visible artifact;
- all generated-output paths resolve below `VERUS_SKILL_RUN_ROOT`.

Fail:

- unresolved fourth task;
- unresolved full-proof scoring target;
- any ambiguity about what a model can see.

### Stage B: Codex fidelity smoke

Run a fresh one-task Codex H0 twice.

Pass:

- each run has a fresh workspace;
- immutable input hash is unchanged;
- every completed command event records command, output/status, and exit code,
  or is explicitly marked payload-incomplete;
- every edit is recoverable as a patch or before/after snapshot;
- each Verus/Lynette record is bound to the evaluated candidate hash;
- final independent Verus and Lynette results reproduce the stored status;
- usage is present and JSONL parses without error.

Fail and stop:

- reference answer or prior trajectory is visible;
- verifier result cannot be tied to a code hash;
- event loss prevents reconstruction of the visible agent loop;
- Codex is not the frozen model/configuration.

### Stage C: OpenRouter Qwen fidelity smoke

Use a credential supplied only through `OPENROUTER_API_KEY` in the process
environment. Do not put it in a command, config, prompt, manifest, exception,
or log.

Run:

1. an offline fake-response adapter test;
2. a redaction canary test;
3. one minimal provider preflight;
4. one one-task Qwen agentic smoke after the preflight passes.

Pass:

- the response identifies `qwen/qwen3.6-27b`;
- sanitized request/response records, usage, finish reason, latency, and request
  count are present;
- host-executed tools and edits are fully recorded;
- independent Verus/Lynette validation is bound to the final code hash;
- repository and run-root scans find no credential or canary.

Provider failure policy:

- authentication failure: stop and request a corrected runtime credential;
- no credit/payment-required: declare OpenRouter unavailable and enable the
  local-Qwen sensitivity arm;
- rate limit: bounded backoff, then stop if the frozen retry budget is spent;
- transient server/network failure: bounded retries, then local fallback only
  after the failure is recorded;
- model mismatch or malformed response: stop; do not silently fall back within
  the same run.

### Stage D: token-first smoke and first round

Run the six-call engineering smoke. If valid, freeze the first token
meta-skill, run the full `3 x 4` candidate matrix, and compare each candidate
with H0.

Promote a token skill for reflection only if:

- all four task rows are present;
- at least three rows are verifier-valid executions;
- no safety bypass is present;
- the candidate does not improve tokens solely through more failures;
- mean ETtS improves, or the candidate is a useful high/low contrast with a
  clearly diagnosed mechanism.

The meta-agent receives the best, worst, and complete aggregate table. It must
not receive other branches' results.

### Stage E: small-model first round

Start only after Stage C passes and the token branch demonstrates that the
common logging and workspace machinery is stable.

Run the `3 x 4` Qwen agentic matrix. API execution is primary. Local execution
is a separately labeled fallback/sensitivity arm and may not be pooled into
the API mean.

### Stage F: InfoGain debugging and first round

Start after:

- the full proof target/target span is frozen;
- pre and post summary emission points are deterministic;
- the local scorer reproduces cached no-summary scores;
- all sequences fit the declared context policy;
- reference-proof visibility tests pass.

Run four baseline scores, then 12 pre-summary and 12 post-summary scores.

### Stage G: iteration decision

Approve one more iteration per branch only if:

- the branch has no missing or contaminated runs;
- its metric was computed by the frozen policy;
- the first iteration produced a concrete contrast the meta-agent can edit;
- the second round's expected cost is accepted explicitly.

Otherwise stop the branch and record the failure mode. Do not spend another
round merely because the first result is negative.

## 7. Meta-agent behavior

Each meta-agent is a fresh programmatic Codex invocation in a clean workspace.
It sees:

- its objective definition and metric contract;
- its current meta-skill;
- three prior candidate skills;
- per-task aggregate outcomes and dispersion;
- selected best and worst examples;
- branch-local visible traces or compact evidence explicitly allowlisted by
  the visibility contract;
- verifier and safety results.

It does not see:

- another branch's workspace or metric;
- final-test results;
- a reference proof;
- API credentials;
- raw historical data outside the frozen evidence pack;
- hidden model reasoning.

The meta-agent must emit:

1. a diagnosis of the best/worst contrast;
2. one retained principle and one rejected principle;
3. a revised objective-specific meta-skill;
4. exactly three next-round skills;
5. explicit applicability and negative-scope statements for each skill.

The program validates this schema before any solver runs are launched.

## 8. Randomness and pairing

- Freeze task order before generation.
- Record every seed supported by the provider/harness. An unsupported seed is
  `null`, not fabricated.
- Keep generation parameters identical across H0 and the three skills within
  a model/transport arm.
- Pair conditions by task and execution budget.
- Do not require output identity across repeated runs; require contract and
  trace fidelity.
- With only four tasks, report all individual rows, means, and ranges. Do not
  rely on asymptotic significance tests.

## 9. Artifact layout

Each external run contains:

```text
<run_id>/
  contract/
  tasks/
  branches/token/
  branches/small_model/
  branches/info_gain/
  audits/
  summaries/
```

Each solver run contains the normalized files required by
`INFORMATION_CONTRACT.md`. The repository stores only reviewed schemas,
compact aggregate summaries, hashes, and external run pointers.

## 10. Risks and mitigations

| risk | consequence | mitigation / stop rule |
|---|---|---|
| API credential leaks through errors | security incident | env-only injection, sanitized exceptions, canary scan; stop immediately |
| Codex JSONL omits a tool payload | false high-fidelity claim | explicit completeness flags; fail fidelity gate if loop cannot be reconstructed |
| skill adds prompt tokens but saves turns | ambiguous token result | full ledger and ETtS, report component costs |
| fast failures appear cheap | false improvement | zero-success ETtS is infinite; solve rate always co-reported |
| API route silently changes model | invalid comparison | exact response model check; abort sample |
| local fallback mixed with API | confounded small-model result | separate transport arm and summary |
| fourth task selected using skill results | selection leakage | H0-only capped screening and frozen hash |
| reference proof leaks to agent | invalid IG | evaluator-only store and visibility scan |
| meta-agent sees all objectives | implicit scalarization/leakage | separate workspaces and allowlisted reflection packs |
| only one stochastic run | unstable ranking | treat first iteration as pilot; scale repetitions only after fidelity |

## 11. Success criteria for this planning phase

Planning is complete when:

- this plan, the information contract, debug gates, and tracker agree;
- the canonical research memory points to these documents;
- no secret or raw data was added to the repository;
- the next executable action is a model-free fidelity test, followed by the
  one-task Codex smoke;
- no OpenRouter request is made until runtime-secret and redaction tests pass.

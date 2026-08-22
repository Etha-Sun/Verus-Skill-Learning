# GPT GLM skill trajectory case study

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-21T18:00:41`
- status: `complete`

## Objective

Explain, at trajectory level, why the accepted VeruSAGE repair skill made
GPT-5.6 Sol slower on held-out task `0a8f681e5d0104455f3b` while changing
GLM-5.3 from timeout/failure to a verified solution. Separate observable
search-policy effects from unsupported claims about hidden reasoning or stable
causality.

## Context

The task is
`AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods`.
Its source contains one unfinished proof whose postcondition requires the API
list response to contain exactly the matching Pods, successful unmarshalling,
and duplicate-free object, object-key, and Pod sequences.

This is a focused case study within the completed four-model held-out
evaluation:

- `research_memory/projects/verus_self_evolving/experiments/20260821-130358-skillopt-s1-s2-four-model-held-out-evaluation/ENTRY.md`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/aggregate-live/per_task.csv`
- source:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-claude-stratified-80-seed20260814/sources/verified-anvil/unverified/AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods.rs`

All six compared arms use the same task input, actor-specific harness, maximum
reasoning effort, 600-second endpoint, and final Verus/Lynette checks. The only
intended within-actor treatment is blank, S1, or S2 skill text. There is one
retained rollout per condition. The normalized GPT traces report zero visible
reasoning items, so this analysis uses only observable messages, commands,
candidate changes, verifier feedback, and final code.

## Method / Actions

Read-only reconstruction used each arm's `result.json`, `agent_events.jsonl`,
`codex_events.raw.jsonl`, snapshots, final `candidate.rs`, prompt, task-local
skill, and independent validation. Metrics are:

- first edit: seconds from run start to the first non-empty candidate snapshot;
- first pass: seconds from run start to the first actor Verus exit code 0;
- pre-edit/all commands: completed shell commands before the first edit and in
  the full actor trace;
- changed snapshots: distinct post-initial candidate-change boundaries;
- failed Verus: actor verifier invocations returning nonzero;
- patch additions: added lines relative to the frozen task source;
- tokens: cumulative Codex/bridge turn usage, not unique prompt text.

## Raw Comparison

| actor | condition | result | wall s | first edit s | first pass s | pre/all commands | changed snapshots | failed Verus | input/output/reasoning tokens | patch additions | API cost USD |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | blank | solved | 339.54 | 98 | 300 | 10/26 | 8 | 8 | 1,420,284 / 14,431 / 5,969 | 132 | local quota |
| GPT-5.6 Sol | S1 | solved | 479.03 | 112 | 453 | 14/34 | 14 | 14 | 2,401,761 / 19,004 / 8,282 | 182 | local quota |
| GPT-5.6 Sol | S2 | solved | 464.71 | 154 | 437 | 34/56 | 13 | 13 | 2,448,621 / 18,705 / 6,456 | 134 | local quota |
| GLM-5.3 | blank | timeout, unsolved | 602.49 | 104 | none | 24/63 | 21 | 25 | 3,056,640 / 17,227 / 5,040 | 147 | 0.970772 |
| GLM-5.3 | S1 | solved | 558.54 | 123 | 524 | 20/49 | 12 | 12 | 3,566,555 / 24,716 / 12,965 | 126 | 1.131663 |
| GLM-5.3 | S2 | solved | 502.87 | 58 | 418 | 13/46 | 15 | 13 | 3,488,902 / 21,635 / 8,835 | 185 | 1.099425 |

## Findings

### 1. GPT slowdown is search-policy overhead, not skill-reading overhead

Observation: relative to blank, GPT S1 and S2 take 139.49 seconds (+41.1%) and
125.17 seconds (+36.9%) longer while preserving the same solved outcome. Their
cumulative input tokens rise by 69.1% and 72.4%. Reading the skill delays the
first Verus call by only about six to seven seconds, so the skill file's length
does not explain the total delta.

The observable expansion happens in two phases. Before editing, blank executes
10 commands and edits at 98 seconds; S2 executes 34 commands and edits at 154
seconds after auditing the target, API transition, resource/object definitions,
and vstd collection lemmas. After the first edit, blank reaches its first pass
in 202 seconds, versus 341 seconds for S1 and 283 seconds for S2. S1/S2 create
14/13 changed checkpoints and encounter 14/13 failed Verus checks, versus 8/8
for blank.

Interpretation: GPT already has a workable end-to-end construction. The shared
S1 instructions to classify first, inspect contracts and nearby helpers before
unfolding, name predicates, prove explicit semantic bridges, and test one
hypothesis per edit turn that construction into a conservative decomposition.
Every extra tool cycle replays a large cached context, which explains why the
cumulative input count grows much more than the skill text itself.

The generated code shows the same effect. Blank closes several returned-object
facts in one combined quantified block and finishes with 132 added lines. S1
splits the facts across multiple quantified proofs, repeatedly chooses map
witnesses, and grows to 182 added lines. S2's added exact-shape guidance partly
repairs that answer bloat: it binds stable local closures and combines the
per-object facts into one `assert forall ... implies { ... }`, returning to 134
added lines and finishing 14 seconds sooner than S1. It still performs much
more pre-edit inspection and verifier-guided micro-iteration than blank.

Implication: on this already-solvable GPT case, the skill acts more like a
redundant procedural prior than missing knowledge. It improves explicitness
and auditability but spends search budget without improving the endpoint.

### 2. GLM succeeds because the same policy supplies a missing injectivity bridge

Observation: blank GLM never obtains a passing actor checkpoint. It makes 21
candidate changes and 25 failed Verus calls before the 600-second cutoff. Its
final candidate is close, but independent validation leaves exactly two
assertions open:

1. `resp_pods[i].metadata == resp_objs[i].metadata`;
2. `resp_objs[i].object_ref() == resp_objs[j].object_ref()` after assuming the
   two unmarshalled Pods are equal.

Those are semantic-bridge failures, not missing top-level response structure.
The blank trace already found finite-set helpers, set extensionality, and map
witnesses, but it jumped from equality of unmarshalled Pods to equality of
dynamic-object references without establishing the fields required by
`object_ref`.

S1 and S2 instead mirror the shared skill's bridge recipe. They bind named
predicates, establish returned-object properties under explicit quantified
antecedents, and reduce duplicate-freedom to map-key injectivity. In S1 the
successful chain is explicit:

`equal Pod views -> equal metadata -> equal name/namespace/kind -> equal
ObjectRef -> equal resource key -> equal stored object -> contradiction with
the response sequence's no-duplicates fact`.

S2 makes the prerequisite `obj.metadata.name is Some` part of its per-object
quantifier, then repeats the same chain for both mapped Pods and mapped object
references. It also uses stable locals `list_pred`, `owned_pred`,
`unmarshal_err_pred`, `pod_map`, and `object_ref_map`, directly reflecting the
skill's higher-order-shape instruction.

This changes the search dynamics as well as the final proof: S2 edits at 58
seconds instead of 104, uses 46 rather than 63 shell commands, and cuts failed
Verus checks from 25 to 13. Its first valid proof appears at 418 seconds, leaving
time to handle a Lynette rejection caused by a top-level macro import, qualify
the macro inside the proof, and pass both acceptance checks.

Implication: GLM blank had the ingredients but lacked a disciplined way to
compose them. The skill externalizes that composition policy and prevents the
late-stage leap that remained unjustified at timeout. This is a capability
gain on the retained rollout, not a token- or dollar-efficiency gain: S2 uses
14.1% more cumulative input tokens and costs 13.3% more than the censored blank
run.

### 3. The successful ingredient is mainly the shared S1 core

GLM already changes from unsolved to solved under S1, before S2 adds Task
Boundary and Exact Quantifier/Higher-Order Shapes. Therefore the narrowest
supported mechanism is the S1 core: contract-first diagnosis, named local
predicates, explicit extensional/field bridges, concrete witnesses, and bounded
iteration. S2's additions plausibly improve proof organization and speed in
this realization, but S1 versus S2 is not a clause-level causal ablation.

### 4. Evidence boundary

The within-actor inputs and harnesses are aligned, and command counts, token
counts, snapshots, verifier failures, and final proof shapes all support the
mechanism above. Nevertheless, one stochastic rollout per condition cannot
establish that the skill always slows GPT or always enables GLM. No hidden
chain of thought is exposed, so claims are restricted to observable behavior.

## Evidence

Primary raw directories, all read-only:

- GPT blank:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-blank-reference-aligned-retryfix-20260821/predictions/0a8f681e5d0104455f3b/`
- GPT S1:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-s1-reference-aligned-retryfix-20260821/predictions/0a8f681e5d0104455f3b/`
- GPT S2:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-s2-reference-aligned-retryfix-20260821/predictions/0a8f681e5d0104455f3b/`
- GLM blank:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-glm-blank-reference-retryfix-20260821/predictions/0a8f681e5d0104455f3b/`
- GLM S1:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-glm-s1-reference-finalbridge-20260821/predictions/0a8f681e5d0104455f3b/`
- GLM S2:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-glm-s2-reference-finalbridge-20260821/predictions/0a8f681e5d0104455f3b/`

High-value anchors:

- GLM blank final verifier errors: `result.json`, validation stderr at candidate
  lines 3855 and 3857.
- GLM S1 successful field bridge: `candidate.rs` lines 3847-3871.
- GLM S2 named predicates and prerequisite field fact: `candidate.rs` lines
  3762-3785; Pod/ObjectRef bridge: lines 3850-3875 and 3896 onward.
- GLM S2 trajectory phase messages: `agent_events.jsonl` events 47, 76, 141,
  186, 191, and 203; first valid Verus at event 183.
- GPT blank/S1/S2 first changed snapshots: events 41, 52, and 112; first valid
  actor Verus: events 105, 159, and 220.

## Decision / Next Step

Do not add this held-out task's exact proof chain to the skill. Test the
mechanism on task-disjoint development items with repeated seeds:

1. ablate the shared skill into contract-first inspection, extensional/field
   bridges plus named predicates, and bounded one-hypothesis iteration;
2. predeclare first-edit latency, pre-edit commands, changed checkpoints,
   verifier failures, cumulative tokens, solved rate, and proof size;
3. test an adaptive route that retains bridge guidance for GLM-like stalled
   searches but caps redundant pre-edit inspection and micro-iteration for
   already-capable actors;
4. keep held-out outcomes diagnostic-only and do not update locked S2 from
   this case.

Raw run data and the frozen task source were not modified.

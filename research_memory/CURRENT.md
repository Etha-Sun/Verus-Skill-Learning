# Current Research State

Last updated: 2026-07-21

## Active Direction

The user clarified that trace analysis, skill learning, and self-evolution are
parallel research workstreams, with trace analysis currently receiving the
main emphasis. Their code should not share one flat `verus_self_evolve`
namespace: stable trace contracts belong below all workstreams, while
self-evolution is an experiment/orchestration layer that may consume trace
analysis, learned skills, and evaluation. Information gain remains a secondary
offline artifact ranking and diagnosis signal, not the main system endpoint.

Repository asset audit:

- `research_memory/projects/verus_self_evolving/notes/20260720-175648-trace-analysis-mainline-repository-asset-audit/ENTRY.md`
- `research_memory/projects/verus_self_evolving/notes/20260721-140725-repository-architecture-boundary-review/ENTRY.md`

Near-term repository decision: preserve the existing code package at the
GitHub root and add parallel top-level workstream directories (`refine-logs/`,
`research_memory/`, trace analysis, ATLAS, and related reviewed artifacts).
Defer both the large `verus_skill_learning` package reorganization and the
exact outer-workspace mirror. Promote code into `src/` only when it has a
reusable interface and tests.

Core hypothesis:

> Historical Verus repair traces can be compressed into verifier-grounded
> prompts or skills that preserve hands-off-level solved rate while reducing
> uncached inference tokens, wall time, or required model scale. Promotion
> requires project-held-out live reruns; offline information gain alone is
> insufficient.

Current design principle:

- Never block the LLM's internal reasoning or broad hands-off-style exploration.
- Inject rules only at selected execution/decision points as hard safety checks,
  soft recommendations, critique prompts, retrieval hints, or sampling priors.
- Let LLMs propose/update rules and skills from hands-off/hands-on traces; promote
  them only after verifier-grounded replay, held-out checks, or live reruns.
- New reward candidate from the July 4 meeting:

  ```text
  IG(artifact; trajectory_t)
    = score_T(gt_proof | trajectory_t, artifact)
      - score_T(gt_proof | trajectory_t)
  ```

  where `artifact` can be a rationale, counterexample-like explanation, skill,
  or sampled skill. InfoGain-RAG is the closest literature analogue: it scores
  context by the confidence gain it provides for generating a ground-truth
  answer.

## Current Scaffold

Executable repository:

- repository root, with reusable code in `src/` and documentation in `docs/`
- generated runs under `VERUS_SKILL_RUN_ROOT`
- historical runs under the legacy archive described by
  `.agent-context.local.md`

Latest committed scaffold:

- `37581a0 Document public research workspace layout`
- `fdcf3da Add experiment planning and audit records`
- `56193d0 Add ATLAS trace reproduction adapter`
- `eb4b9bc Add trace-analysis research workstream`
- `5d21a81 Organize repository documentation and results`
- `869af8f Add per-user data source selection`
- `1446435 Record hands-off execution plan`
- `b085d64 Add noninteractive hands-off harness`
- `4ad9339 Add balanced hands-off selection`
- `c05b553 Add leakage-safe corpus inventory`
- `b2071fb Wire information-gain CLI and action ontology`
- `23d109c Add three-target diagnostics and plots`
- `3bcbce7 Add paired information-gain analysis`
- `d788d26 Add teacher-forced logprob scoring`
- `d554ed9 Add information-gain probe preparation`
- `7ebc542 Record offline replay baseline`
- `743c40b Add offline evaluation CLI and reporting`
- `5c84b44 Add offline replay scoring`
- `08f5206 Add repair rule mining`
- `e8b7311 Add Verus motif classification`
- `68107cb Add Verus trace models and loader`
- `0b57098 Initialize verus-skill-learning package`

## Repository And Per-User Data Source Decision (2026-07-20)

The active code repository should be published as `verus-skill-learning`.
Each collaborator supplies and selects an independent local data source through
`VERUS_SKILL_DATA_ROOT` and `VERUS_SKILL_DATA_LAYOUT`; datasets do not need to
be shared or migrated. Large run outputs remain under the local
`VERUS_SKILL_RUN_ROOT`. The code repository keeps contracts, tests, small
fixtures, and reviewed compact summaries, but not raw traces or complete run
directories.

Implementation status: the approved unpublished history was rebuilt as 18
module-scoped commits dated across 2026-07-02 through 2026-07-20 on local branch
`main`. Its committed tree is identical to the pre-rewrite tree retained on
`backup/pre-publish-history-20260720`. All 51 tests pass. Concurrent M1 edits to
`PLAN.md` and `CHECKLIST.md` were restored byte-for-byte and remain uncommitted.
No data was moved or modified. The 18 commits are published on public GitHub
repository `Etha-Sun/Verus-Skill-Learning`, branch `main`, at
`5d21a8195a9137d4cfde89ea14c03131a76cb232`. Local `main` tracks
`origin/main`; the local and remote SHA values match.

Public-safe top-level research workstreams are published on `main` at
`37581a0`. The snapshot excludes raw datasets, full run directories, caches,
model/API responses, meeting transcripts, large derived trace artifacts, and
personal absolute paths. Collaborators continue to select their own data
through `VERUS_SKILL_DATA_ROOT`; no dataset migration is needed.

Canonical decision:

- `research_memory/projects/verus_self_evolving/decisions/20260720-172029-per-user-data-source-selection-and-repository-cleanup/ENTRY.md`

## Agent Context Migration (2026-07-21)

The GitHub repository root is now the active agent workspace. Root
`AGENTS.md` makes repo-local `research_memory/` canonical and overrides the
global research-memory skill's legacy write target. Active code and docs paths
now resolve below `src/` and `docs/`; historical run references are explicitly
legacy archives below `VERUS_SKILL_DATA_ROOT`, while new generated runs belong
below `VERUS_SKILL_RUN_ROOT`.

Migration validation rebuilt the memory index, accepted the legacy data layout,
and passed all 54 core unit tests. The local Copilot, Verus, and Lynette
executables resolve; Lynette 0.0.0 is configured through the ignored local
`.env`. Optional ARIS project skills are installed from a stable external
checkout and remain local-only. No raw data or historical run was modified.

Phase 1 output-path hardening now requires every active CLI and experiment
writer to place generated artifacts below `VERUS_SKILL_RUN_ROOT`. The validator
also requires that root to exist, be writable, and remain disjoint from both
the repository and `VERUS_SKILL_DATA_ROOT`. The configured external root was
created and passed validation in the actual execution environment. A
model-free harness dry-run completed at
`${VERUS_SKILL_RUN_ROOT}/phase1-output-path-smoke-20260721/`; 54 core tests and
the 5 standalone ATLAS adapter tests pass. Restricted sandbox processes still
need explicit permission to write to the external root, as intended.

Latest offline metrics:

| policy | covered failed | saved failed tokens | false-stop rate | peer diff |
|---|---:|---:|---:|---:|
| generic | 1,038 | 800,760,044 | 0.112951 | 0.748705 |
| project-aware | 539 | 548,995,746 | 0.039030 | 0.748252 |
| motif-aware | 227 | 309,382,084 | 0.005322 | 0.777778 |

Interpretation:

- Generic rules cover more failures but are risky.
- Motif-aware rules are safer and better support the need for Verus-specific
  policy.
- These are offline replay results, not final live repair improvements.

## Qwen3.6 Three-Target IG Pilot (2026-07-14)

R027-R035 are complete on local `<model-root>/Qwen3.6-27B` using HF exact chunked teacher forcing. The formal matrix contains 3 traces, 6 accepted trajectory states, 3 targets, and 7 artifact/control conditions (126 cases). All sequences fit the 131,072-token context; no truncation occurred. The run saved 1,499,498 baseline/artifact token-probability rows and completed in about 51m33s.

Matched-control specific IG results:

| target | mean total bits | mean bits/target-token | positive states |
|---|---:|---:|---:|
| action | 0.9612 | 0.309137 | 4/6 |
| patch span | 12.7686 | 0.017837 | 4/6 |
| full proof | 22.3031 | 0.001580 | 6/6 |

The control mean must not hide individual-control failures:

- action evidence loses to irrelevant on average and wins only 2/6; it also wins only 3/6 against shuffled;
- patch wins 5/6 against irrelevant but has negative mean difference against shuffled;
- full proof wins 6/6 against both irrelevant and shuffled.

Independent GPT-5.5 xhigh integrity verdict: `WARN`. Arithmetic, hashes, target construction, and result existence pass. This remains a `self_supervised_proxy` on only 3 traces / 6 states, not a downstream agent-improvement evaluation. Actual scorer backend is HF. The run used observed targets only; no 22-way candidate-normalized action distribution was run.

Canonical artifacts:

- report: `refine-logs/EXPERIMENT_RESULTS_20260714_162614.md`
- audit: `refine-logs/EXPERIMENT_AUDIT_20260714_163500.md`
- legacy run archive:
  `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/qwen36_three_target_ig_20260714/r032_r034_all_states_observed/`
- memory: `research_memory/projects/verus_self_evolving/experiments/20260714-164002-qwen3-6-three-target-information-gain-pilot/ENTRY.md`

## Hands-Off Distillation Priority (2026-07-17)

The latest group discussion narrows the immediate goal. Start from successful
frontier-model/agent hands-off traces under `claude_sonnet_gpt5/`, distill
reusable proof-repair knowledge, and inject it into real held-out Verus repair
runs. A short unstructured prompt is an acceptable first artifact; methodology
novelty and self-evolution are not the first gate.

Operational definition of beating hands-off:

- preserve comparable verifier solved rate while using substantially fewer
  inference tokens; and/or
- let a substantially smaller model approach the no-knowledge frontier-model
  baseline.

Primary system metrics are solved rate, uncached tokens per task and per solved
task, wall time/tool iterations, and model size/serving cost. Artifact IG and
information density remain secondary offline selection metrics; they are not a
substitute for live agent improvement. Distillation cost must be reported
separately and amortized over downstream tasks.

Decision: run a leakage-safe corpus inventory and a paired distilled-prompt
live baseline before RL, large self-evolution loops, or broad harness mutation.

Memory entry:

- `research_memory/projects/verus_self_evolving/meetings/20260718-112059-hands-off-trajectory-distillation-and-inference-cost-objective/ENTRY.md`

Long-horizon experiment roadmap:

- canonical plan: `refine-logs/EXPERIMENT_PLAN.md`
- tracker: `refine-logs/EXPERIMENT_TRACKER.md`
- memory:
  `research_memory/projects/verus_self_evolving/experiments/20260719-103727-hands-off-trace-distillation-long-horizon-experiment-roadmap/ENTRY.md`

## Hands-Off M0 Integrity Execution (2026-07-20)

R036-R038 are complete. The frozen inventory covers 9,383 trajectories:
3,347 original train, 3,015 dev, and 3,021 sealed-test rows. No sealed MA/NR
trace content was read. The initial leakage audit found IronKV tasks nearly
duplicated in the sealed NR evaluation; fixed-point quarantine removed six
train traces, leaving 3,341 effective train rows and zero exact-name,
exact-code, or >=0.90 near-code overlaps.

The unified Copilot harness now records source/base-prompt/payload hashes,
provider configuration, usage, timeouts, candidate hashes, Verus results, and
Lynette target-mode results. Thirteen tests and deterministic end-to-end
integration pass. Historical usage is available for only 283/3,347 train logs,
all Opus 4.5, so future cost claims must use live harness accounting.

M0 classification is `GO` for train-only R040-R041. A Qwen3.6-27B mechanical
smoke through Copilot CLI recorded usage, candidate, Verus, and Lynette results
for H0/H1/H2. Input/output tokens were 1.2M/11.1k, 1.1M/10.1k, and
1.3M/11.8k; wall times were 516/478/560 seconds. Verus failed 3/3 while Lynette
passed 3/3, and all canonical runs exhausted the 32,768-token context. This is
measurement and failure-path evidence only, not a knowledge-effect result.

The harness now parses the current Copilot token footer and preserves footer
output on timeout; 15 tests pass. QwQ direct/adapter attempts did not produce
executable tool calls. Final Qwen cleanup returned GPUs 0-3 to 1 MiB / 0%.
R040 is complete. The canonical attempt3 selected 30 train traces with unique
normalized tasks and sources: 15 Anvil, 15 IronKV, and six each from Opus 4.5,
Sonnet 4, Sonnet 4.5, GPT-5, and o4. All selected log and verified paths exist;
sealed content reads remain 0. Attempts 1-2 are retained as failed audits. R041
train-only prompt distillation is next. R042 frontier-model evaluation remains
blocked until cloud authentication is available.

Canonical entry:

- `research_memory/projects/verus_self_evolving/experiments/20260720-001046-m0-hands-off-corpus-integrity-and-unified-harness-execution/ENTRY.md`

## Qwen Capability Calibration Gate (2026-07-21)

The one-task Qwen3.6 mechanical smoke is insufficient for selecting a local
knowledge-effect diagnostic: it cannot distinguish model capability, task
difficulty, context/scaffold failure, or an unrepresentative task. Before R041,
the active execution queue now inserts R040A-R040D:

1. freeze 30 independent train-domain calibration tasks, balanced 15 Anvil /
   15 IronKV and exact/near-disjoint from the 30 R040 distillation traces;
2. run one Qwen3.6-27B H0 screen per task under the frozen Copilot harness;
3. add two H0 repetitions for predeclared boundary candidates;
4. freeze up to three `pass`, `near_miss`, and `stalled` tasks before any
   H1/H2 outcome is viewed.

R041 still distills the <=800-token H2 prompt and length-controlled H1 from
the independent R040 traces. R041A then runs the frozen prompts on the frozen
tiers. These selected-case results are mechanism diagnostics only; held-out
R042-R053 live evaluation remains necessary for solved-rate or token-efficiency
claims. Context-ineligible cases are reported separately rather than labeled
as reasoning failures.

Read-only preflight found 2,752 metadata-eligible rows / 425 unique train tasks
after exact R040 exclusions, so the pool is sufficient. Data/run layout
validation passes and sealed reads remain 0. At planning time all four local
L40S GPUs were at 99-100% utilization, so live R040B deployment waits for GPU
availability; planning, CPU audit, code, tests, and model-free sanity proceed.

R040A is now complete at
`${VERUS_SKILL_RUN_ROOT}/r040a_qwen_calibration_20260721_attempt4/`: 30 unique
canonical originals, 15 Anvil / 15 IronKV, and 10 small / 10 medium / 10 large.
Every selected source fails its source Verus precheck, while every paired
standard-trace answer passes the current Verus and Lynette comparison. R040
exact/near overlap and sealed content reads are zero. The frozen screen manifest
and model-free sanity are under
`${VERUS_SKILL_RUN_ROOT}/r040b_qwen_screen_20260721_manifest_attempt3/` and
`${VERUS_SKILL_RUN_ROOT}/r040b_sanity_20260721_attempt3/`; all frozen source,
prompt, model-config, tool, timeout, and context identities match. All 69 tests
pass.

Independent final review is `GO` for R040B attempt4. Its non-blocking launch
note is to reconfirm the live vLLM endpoint and frozen 32,768 context after the
GPUs become free. Review: `refine-logs/EXPERIMENT_CODE_REVIEW_20260721_175704.md`.

The external workload was subsequently released. R040B completed under
`${VERUS_SKILL_RUN_ROOT}/r040b_qwen_screen_20260721_live_attempt2/` using the
frozen Qwen3.6-27B alias, TP=4, 32,768-token context, and Qwen3/Qwen3-Coder
reasoning/tool parsers. All 30 result and manifest records are present and
their frozen identities match. Strict security-valid solve is 7/30 (23.3%):
7 pass, 11 stalled, 10 timeout/infrastructure failures, and 2 unsafe; usage is
available for 21/30. One timeout produced no candidate, which is explicitly
recorded rather than missing evidence. The rank-1 Copilot log also records 12
temporary Verus API probes written under `/tmp`, contrary to the prompt's
workspace-only instruction; they were removed after exact enumeration, the
formal run logs remain intact, and raw corpus data were untouched. No H1/H2
outcome has been viewed.

R040B also falsified the planned three-tier selector as written. All 30 source
programs have exactly one Verus error, while `near_miss` requires a strictly
lower candidate error count without passing. Therefore the zero observed
`near_miss` count is structurally expected: zero errors normally implies pass.
The three-trajectory rationale comparison remains useful as a qualitative
mechanism pilot, but its middle case must be frozen from H0-only evidence as a
`closest_failure` (proof-safe, compilable, localized residual proof failure),
not relabeled as `near_miss`. The comparison should use one stable pass, one
predeclared closest failure, and one stable stalled task, with rationale derived
only from the independent R040 traces. It cannot support a solve-rate claim.

R040C is complete. No candidate was stable `stalled`, so the predeclared
stable-stalled branch was not silently forced. An H0-only adaptive qualitative
branch froze exactly one strict `stable_pass` (pass/pass/pass), one strict
`stable_closest_failure` (closest/closest/closest), and one `unstable`
(stalled/pass/pass, with no unsafe or infrastructure outcome). The unstable
case diagnoses generation consistency and specification discipline; it is not
a claim that the model has no proof idea. R040D-A and the immutable 27-record
R041A manifest are under
`${VERUS_SKILL_RUN_ROOT}/r040d_adaptive_cases_20260722_attempt1/` and
`${VERUS_SKILL_RUN_ROOT}/r041a_contrast_20260722_attempt1/`. R041A reuses nine
H0 records and is now running the 18 new H1/H2 records sequentially in screen
`r041a_contrast_20260722`; it remains qualitative and not held-out evidence.

R041 prompt distillation is complete. One global H2 was distilled from compact
patch/log excerpts of the independent 30 R040 train traces, then safety-reviewed
to prohibit all bypasses and use the actual Verus+Lynette validation. H1 is a
trace-free generic control. The canonical reviewed freeze has H1=633 and
H2=632 Qwen tokenizer tokens (0.16% delta), no frozen task identifiers, and no
permissive bypass advice. H2 is global, not task-specific. Distillation usage
was 28,206 input / 634 output tokens; AI-agent review/edit time was 5 minutes
and human edit time was 0. Canonical artifacts are
`${VERUS_SKILL_RUN_ROOT}/r041_prompt_distillation_20260722_attempt1/` and
`${VERUS_SKILL_RUN_ROOT}/r041_frozen_prompts_20260722_attempt3/`; the compact
reviewed prompt copy is `refine-logs/r041_prompts/`.

An independent R041 review initially returned NO-GO on raw-data containment,
transitive provenance, edit-cost labeling, and missing negative tests. All four
blockers were fixed; the follow-up verdict is GO with 76 repository tests
passing. Review artifact:
`refine-logs/EXPERIMENT_CODE_REVIEW_20260722_132102.md`.

Canonical entry:

- `research_memory/projects/verus_self_evolving/experiments/20260721-172129-qwen-capability-calibration-gate/ENTRY.md`

## Important Caveat

Current rule mining can overfit if rules are mined and evaluated on the same
tasks. The next serious experiment must add split-aware evaluation:

- no exact-task skeleton in eval,
- dev/test split for thresholds,
- task/model/project split variants,
- report solved-rate preservation in addition to token savings.

Architecture provenance caveat:

- The observed repair scaffold is grounded in VeruSAGE-style code/docs, not an
  invented architecture from our trace analysis.
- Public source: `https://github.com/microsoft/verus-proof-synthesis/tree/main/verusage`.
- Local source: `<scratch-root>/RL-verus-1129/autoverus/verusage`.
- Local checkout caveat: the VeruSAGE directories appear untracked in that git
  working copy, so commit-level provenance should be verified before paper
  claims.
- Memory note:
  `research_memory/projects/verus_self_evolving/notes/20260703-093115-verusage-repair-scaffold-provenance-audit/ENTRY.md`.

## ATLAS Taxonomy Pilot (2026-07-11)

ATLAS commit `afbf010117ce` was reproduced on a leakage-safe sample of 40
unique VeruSAGE tasks using local Codex `gpt-5.6-sol/high`. The final adaptive
taxonomy has 28 codes (A=6 system, B=11 role, C=11 Verus-domain), and all 36
Codex calls completed successfully. The 11 C codes cover quantifier
instantiation, case analysis, lemma applicability, loop invariants, bounded
integer semantics, postconditions, unsupported assertions, invariant
preservation, SMT interpretation, liveness/fairness, and induction.

Artifacts:

- report: `atlas-verusage-reproduction/runs/pilot_v1/REPORT.md`
- taxonomy: `atlas-verusage-reproduction/runs/pilot_v1/taxonomy_sol_high_v2/taxonomy.json`
- split/source manifest: `atlas-verusage-reproduction/runs/pilot_v1/input_v2/manifest.json`
- metric contract: `atlas-verusage-reproduction/runs/pilot_v1/json/metric_contract.json`
- memory entry:
  `research_memory/projects/verus_self_evolving/experiments/20260711-095153-atlas-adaptive-failure-taxonomy-reproduction-for-verusage-traces/ENTRY.md`

Verdict: taxonomy induction is feasible and `trusted_with_caveats`; it is not
yet a validated failure detector. The cross-model diagnosis gate has now run on
the same frozen taxonomy and all eight held-out FAILED/TIMEOUT traces using
local Qwen3.6-27B and gpt-5.6-sol/high. A post-hoc strict audit verifies 8/8
schema/code-valid responses per arm, zero vendor code coercions, and identical
visible classifier-prompt hashes for all eight pairs. Exact code and category
agreement are both 7/8: Qwen used A.4 four times and B.7 four times; the large
model used A.4 five times and B.7 three times. This is a one-repetition
operational comparison, not diagnosis accuracy or a pure model-size effect;
the taxonomy was generated by the large model, transports differ, and no human
gold labels exist. The per-trace blinded evidence/recovery audit is complete. Canonical raw
outputs and strict audit are under
`${VERUS_SKILL_RUN_ROOT}/atlas_paired_eval_20260722_attempt1/`.

The completed per-trace blinded audit found nearly identical evidence reading
(Qwen 16 vs large 15 out of 16), but a repeated downstream quality gap:
root-cause specificity was 11 vs 14 and recovery actionability was 9 vs 16;
total was 36 vs 45, with the large model winning 7/8 pairs. The gap repeats in
FAILED (3/4) and TIMEOUT (4/4) strata. The useful takeaway is therefore not
that Qwen cannot read the trace or choose the coarse label; it usually can.
The larger model more often converts the trace into a task-specific causal
diagnosis and targeted next repair step, while Qwen more often falls back to
generic budget/strategy advice. This is still one repetition with no gold and
does not establish a pure scale effect. Compact report:
`refine-logs/ATLAS_PAIRED_RESULTS_20260722_175218.md`.

## Next Recommended Action

Monitor the 18 active R041A H1/H2 records and complete the blinded ATLAS
evidence/recovery audit. Analyze R041A only after all records pass identity and
safety checks. Use ATLAS label agreement as a diagnostic, not accuracy; consider
extra repetitions or independent small-model taxonomy induction only if the
blinded audit reveals a repeated grounded difference. R042 remains a separate
held-out frontier baseline and is not completed by these qualitative pilots.

### Historical: July 13 control-null action pilot decision

R022-R026 are complete. The six-state pilot passes mechanical integrity but fails the predeclared method gate:

- mean specific gain: `-0.2079 bits`;
- positive states: `2/6`;
- evidence wins against same-error/shuffled/irrelevant: `3/6`, `2/6`, `2/6`;
- evidence mean conditional PMI: `-0.1922 bits`;
- all six evidence cases have negative raw target-token IG, mean `-2.2796 bits`.

The fixed A-V candidates carry only `5.00e-12` to `3.96e-10` raw next-token probability mass. Candidate-normalized PMI is therefore a forced-choice conditional diagnostic, not QwQ's natural action policy. `irrelevant_archive` is only a semantic negative control; its positive mean PMI is evidence that raw positive IG is confounded, not evidence that the control is useful.

Decision: STOP patch/full-proof scoring and trace scaling under the current plan. First redesign the scoring interface so the model naturally enters a scoreable action channel, or score actual agent-generated reasoning/actions. Then reconstruct artifacts from authentic trajectory diagnostics and rerun the matched-null gate.

This STOP decision applied to the earlier QwQ/fixed-candidate setup. It was superseded for measurement exploration by the Qwen3.6 observed-target experiment above; it remains relevant evidence that action-only forced-choice PMI was confounded.

Latest artifacts:

- report: `refine-logs/EXPERIMENT_RESULTS_20260713_141542.md`
- audit: `refine-logs/EXPERIMENT_AUDIT_20260713_140634.md`
- legacy analysis archive:
  `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/control_null_ig_20260713/r025_six_states/analysis/analysis_summary.json`
- legacy state-level visualization archive:
  `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/control_null_ig_20260713/r025_six_states/analysis/figures/statewise_three_way_pmi.png`
- memory: `research_memory/projects/verus_self_evolving/experiments/20260713-141547-control-null-direct-action-information-gain-pilot/ENTRY.md`

Previous plan context follows; its patch/full-proof and scaling steps are now blocked by the July 13 STOP decision.

Follow the corrected `information_gain_reward_probe` experiment plan:

- Plan: `refine-logs/EXPERIMENT_PLAN.md`
- Tracker: `refine-logs/EXPERIMENT_TRACKER.md`
- Latest experiment entry:
  `research_memory/projects/verus_self_evolving/experiments/20260711-145632-corrected-action-information-gain-pilot-and-audit/ENTRY.md`

Run order:

1. R015: 11 scorer/provenance tests pass.
2. R016: one-state QwQ action-distribution smoke passes measurement invariants.
3. R017: 3 traces / 7 states completed, but the artifact-quality gate failed.
   Trace rationale beats shuffled in `3/7` states and irrelevant in `2/7`.
4. R017-v2: 6 locally accepted action states are prepared with a frozen
   22-action ontology, 100% observed coverage, and source provenance.
5. Next, replace fixed templates with trajectory-evidence artifacts and create
   randomized tokenizer-matched controls.
6. Reopen patch-span and full-proof scoring only after the corrected action
   artifact gate passes. These long targets remain in scope.
7. Scale to held-out task groups only after the same gate passes.

Current metric decision:

- main formula is `log P(target | state_t, artifact) - log P(target | state_t)`;
- record per-token probability and logprob tables for both baseline and
  artifact-conditioned scoring;
- action IG, full-proof IG, and patch-span IG are parallel first-pass metrics;
- motif/TLA artifact is nice-to-have, not first-pass must-run.

July 11 metric update from PlugMem (arXiv:2603.03296):

- Interpret action log-ratio as Decision Information Gain/PMI; report bits
  (`log2`) or explicitly convert from natural-log units.
- Add skill information density:
  `rho_i = action_PMI_i / exact_intervention_token_count_i` and
  `rho_global = sum_i action_PMI_i / sum_i exact_intervention_token_count_i`.
  The denominator includes all chat-template and artifact-wrapper token changes.
- Sweep skill-token budget or retrieved top-k to expose the utility-cost
  frontier and possible context-toxicity region.
- With a canonical finite VeruSAGE action set, add entropy change as a secondary
  diagnostic of whether a skill sharpens or confuses the decision policy.
- Keep verifier solved rate and total live-agent tokens as primary system
  outcomes; IG/density remain offline promotion and diagnosis metrics.
- PlugMem does not cite InfoGain-RAG in the inspected version. Its experiments
  substitute binary correctness/F1/success for probability with smoothing; do
  not copy that operationalization when direct action logprobs are available.
- Corrected QwQ action scoring is engineering-valid, but current artifacts do
  not separate from shuffled/irrelevant controls. No skill-quality claim is supported.

Latest implementation:

- `src/verus_self_evolve/ig_probe.py`
- `src/verus_self_evolve/logprob_scorer.py`
- `src/verus_self_evolve/ig_analysis.py`
- latest results: `refine-logs/EXPERIMENT_RESULTS_20260711_145502.md`
- latest audit: `refine-logs/EXPERIMENT_AUDIT_20260711_145502.md`
- durable tables:
  `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/corrected_ig_20260711/r017_seven_states/analysis/`
- sanity run:
  `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704`
- initial results:
  `refine-logs/EXPERIMENT_RESULTS.md`
- QwQ/vLLM action-primary results:
  - raw prompt:
    `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704/qwq_vllm_action_primary_21/`
  - explicit prompt:
    `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704/qwq_vllm_action_primary_21_explicit/`
  - explicit mean `ig_sum`: trace rationale 1.0817, generic skill 0.8894,
    irrelevant control 0.6295.
  - caveat: irrelevant control is also positive, so current artifacts are not
    yet clean enough for a promotion claim.

## Fast Pointers

- Chinese auto-research progress overview:
  `research_memory/projects/verus_self_evolving/notes/20260720-164659-auto-research-progress-overview-2026-07-20/ENTRY.md`
- Memory index: `research_memory/INDEX.md`
- Project card: `research_memory/projects/verus_self_evolving/PROJECT.md`
- Scaffold design: `docs/architecture.md`
- Eval summary: `docs/eval_summary.md`
- Self-evolving survey: `analysis_verusage_trace_ideas_20260624/auto_research_20260628/self_evolving_and_verus_specificity.md`
- Current selected idea:
  `research_memory/projects/verus_self_evolving/ideas/20260703-100812-non-blocking-verifier-guided-self-evolving-steering/ENTRY.md`
- July 4 meeting digest:
  `research_memory/projects/verus_self_evolving/meetings/20260704-103108-kexin-new-project-3-information-gain-skills/ENTRY.md`
- InfoGain-RAG literature mapping:
  `research_memory/projects/verus_self_evolving/literature/20260704-103229-infogain-rag-reference-for-proof-rationale-reward/ENTRY.md`

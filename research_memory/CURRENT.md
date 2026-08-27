# Current Research State

Last updated: 2026-08-26

## Active Direction

The user clarified that trace analysis, skill learning, and self-evolution are
parallel research workstreams, with trace analysis currently receiving the
main emphasis. Their code should not share one flat `verus_self_evolve`
namespace: stable trace contracts belong below all workstreams, while
self-evolution is an experiment/orchestration layer that may consume trace
analysis, learned skills, and evaluation. Information gain remains a secondary
offline artifact ranking and diagnosis signal, not the main system endpoint.

## Qwen Test-20 Three-Arm Heatmaps (2026-08-26)

The latest Qwen3.8 1200-second blank/S2/Trace2Skill result now has aligned
20-by-3 pass/fail and complete-ledger token-cost heatmaps. They reconcile to
5/20, 7/20, and 6/20 solved and 9,412,193, 8,588,155, and 8,991,255 tokens.
The reusable command accepts one comparison folder and writes both PNGs plus
the plotted CSV below that run folder. This is visualization of the existing
descriptive rollout, not additional method-effect evidence. Canonical entry:
`research_memory/projects/verus_self_evolving/experiments/20260826-225014-qwen-test20-three-arm-heatmaps/ENTRY.md`.

Repository asset audit:

- `research_memory/projects/verus_self_evolving/notes/20260720-175648-trace-analysis-mainline-repository-asset-audit/ENTRY.md`
- `research_memory/projects/verus_self_evolving/notes/20260721-140725-repository-architecture-boundary-review/ENTRY.md`

Near-term repository decision: preserve the existing code package at the
GitHub root and add parallel top-level workstream directories (`refine-logs/`,
`research_memory/`, trace analysis, ATLAS, and related reviewed artifacts).
Defer both the large `verus_skill_learning` package reorganization and the
exact outer-workspace mirror. Promote code into `src/` only when it has a
reusable interface and tests.

## Vskill-0822 Evaluation Alignment Branch (2026-08-22)

The selected integration route is a new `Vskill-0822` branch created from one
reviewed checkpoint commit on `feature/skillopt-verusage-20260812`; the
external Trace2Skill branch will not be merged wholesale. The bounded scope is
to decouple verified proof outcome, completion within the 600-second budget,
and trace fidelity; enable the existing GLM HTTP 429 backoff in the
reference-aligned profile; add a reproducible cached/uncached input plus output
token figure; and pin formal Verus release
`release/0.2025.09.12.bb1f342`.

Timeout candidates that pass independent Verus and Lynette validation and all
safety checks remain solved, while `within_budget` records whether they
completed before timeout. V0/V1/V2 controls whether a trajectory is reusable,
not whether the independently validated proof is correct. Cached input remains
part of cumulative input-token volume and is shown as a segment rather than
subtracted. Before any paid rerun, compare the September 12 release with the
VeruSAGE benchmark commit `ddc66116` in a verifier-only test-20 gate.

Canonical decision:
`research_memory/projects/verus_self_evolving/decisions/20260822-131339-vskill-0822-evaluation-alignment-branch/ENTRY.md`.

Implementation is complete on `Vskill-0822`. The branch now contains immutable
Trace2Skill candidate/snapshot lineage, bridge actor mount/network/seccomp
isolation with exact resume provenance, correctness/budget/safety/fidelity
outcome separation, GLM 429 backoff in both actor profiles, and a fail-closed
September 12 Verus identity contract. The formal release was built and
installed separately from the retained `ddc66116` comparator. The two known
version-sensitive retained GPT blank candidates pass under both binaries.

Model-free validation passes all 146 `skill-evolution-pilot` and
`skillopt-verusage` tests, shell/compile checks, an end-to-end actor-isolation
smoke, and PDF render inspection. The reviewed figure and its 12-row `n=20`
CSV are below
`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/vskill-0822-integration-20260822/figures/`.
Raw datasets and historical runs were not modified. No paid inference was run,
so this integration does not establish score, token, or time parity. Bridge
actors are aligned to the upstream isolation structure; GPT direct remains
explicitly non-isolated until it has a reviewed local bridge. Next action is a
saved `--check-only` preflight, followed by a separately approved fresh run
rather than resuming historical results.

Implementation report:
`skillopt-verusage/refine-logs/VSKILL_0822_TRACE2SKILL_ALIGNMENT.md`.

## Fixed Test Handoff And Main Readiness (2026-08-23)

The fixed test-20 evaluator now accepts either one Markdown skill or a complete
Trace2Skill-style bundle rooted at `SKILL.md`. Bundle contents and executable
bits are inventoried, the content tree uses the Trace2Skill lineage hash,
symlinks are rejected, the artifact is frozen into the run directory, and
supplied skill files must remain unchanged for a solve to count. This is a
final-artifact evaluation handoff; it does not migrate Trace2Skill construction
or add intermediate-candidate promotion.

The 60-second host grace now applies only to actor shutdown. An actor that
ignores SIGINT is force-killed after 15 seconds, while a completed-actor marker
allows the independent Verus and Lynette checks to finish without being cut off
by that grace period. A timeout candidate still counts as solved when both
final checks and input/skill safety pass, with `within_budget=false` recorded
separately.

Microsoft SkillOpt is fixed at commit
`9639719632daecacd1baaa47fe781f3c0253600a`. A tracked patch and bootstrap
verify the complete patched Git tree
`7e207482b0bf0238b21e13976f6f9da5f130072c`, including autocrlf and hidden-index
change defenses. Local trajectory path references are enabled only for the
read-only Codex optimizer; API optimizers retain inline trajectories.

The clean main-readiness suite passes 240 offline tests. No paid inference was
run and no raw dataset or historical run was modified. The tracked test-20 is
a recurring benchmark rather than a sealed test; direct GPT runs are explicitly
diagnostic because external filesystem visibility is not enforced. Three
independent reviewers returned GO for evaluation safety, SkillOpt delivery, and
merge readiness. The only remaining low-risk evaluator caveat is that the
post-run bundle check rejects changes to inventoried files but does not yet
reject newly added files. Commit `d3b9dcb` was fast-forwarded from the clean
curated descendant to `main` on 2026-08-23, and the main-readiness CI passed,
without mixing in the unrelated local research worktree. The next evaluator
hardening action is an exact file-set regression for post-run skill bundles;
future held-out claims still require producer provenance and task-disjoint live
evaluation.

## Trace2Skill Shared Evaluator Integration (2026-08-23)

The selected integration does not cherry-pick the old Trace2Skill experiment
commit wholesale. A clean branch from `origin/main` separates the method
producer from evaluation. The prompt-driven `skill_evolver/` runtime is
vendored from the reviewed `92a1e8a` feature-state snapshot under
`trace2skill_verusage_baseline_test/code/`, receives the four frozen Verus
prompts, and is verified as tree
`e8ef9e77436b0641f0e65b3bc216f202e05235021103a2b7a956009638f88adf`.
Only the thin model client required by skill-generation prompts is retained.
The deprecated `react_agent/` task-solving harness, custom semantic
REDUCE/router, semantic-v4, M_core, candidate gate, and legacy evaluation
bridges are excluded; produced skills are evaluated through the shared Codex
CLI harness. The repository also publishes the neutral seed, producer adapter,
frozen ten-file native official skill bundle,
sanitized provenance, documentation, and a thin evaluation launcher. Raw
training trajectories and normalized analysis records remain external
read-only inputs.

The evaluation launcher delegates to the main fixed-test entry point, so
provider invocation, timeout, token accounting, isolation, and scoring remain
common with SkillOpt; only construction logic differs.

The artifact is byte-identical to commit `92a1e8a`: entry-point SHA-256
`40de0d04f2f4e2b05a0d8187439251f2e381b2f4675c2ef44247519acf9452bd`
and shared `skill-tree-v1` SHA-256
`195ab1294871689873e3bd6d9d2dbfb0a89a0d13b2ea0bdd1f7d716d826437c2`.
The zero-network producer preflight validates the historical 40-record input
(11 error, 29 success, 160 memory items), neutral seed, four prompts, and
integrated producer tree against the recorded runtime contract. Main readiness
passes 254 tests with one optional-Torch skip. GPT evaluator check-only
validates the frozen split and formal Verus `release/0.2025.09.12.bb1f342`. A one-item
pre-merge GPT smoke solved 1/1 with zero timeout and complete V2 trace fidelity.

This smoke is diagnostic, not a formal rerun: it covers only direct GPT, which
remains non-isolated, and does not establish four-provider parity. The next
action is PR review and merge; only then should a separately approved formal
four-provider test-20 rerun start.

Canonical decision:
`research_memory/projects/verus_self_evolving/decisions/20260823-222311-trace2skill-shared-evaluator-integration/ENTRY.md`.

## SkillOpt Multi-File Support Audit (2026-08-21)

Microsoft SkillOpt `main` at `bdfdc30` still defines the core research artifact
as one trainable Markdown string exported as `best_skill.md`. SkillOpt-Sleep
does support loadable frontmatter-bearing `SKILL.md` files and, after merged
PR 212, can independently consolidate, gate, stage, and adopt several existing
skills in one night. That is multi-skill fan-out across separate `SKILL.md`
files, not multi-file evolution within one Anthropic-style skill directory.

The current resolver reads only `<root>/<name>/SKILL.md`; proposals and adoption
each target that one exact file. No current code or open PR jointly optimizes
`references/`, `scripts/`, or `assets/`. PR 134 evaluates one candidate
`SKILL.md` inside a real Superpowers Claude plugin checkout but does not evolve
the companion files. Issues 54 and 145 record explicit maintainer promises for
whole-folder support, yet both were closed without a linked implementing PR.

Canonical audit:
`research_memory/projects/verus_self_evolving/literature/20260821-203750-skillopt-multi-file-and-claude-skill-support-audit/ENTRY.md`.
Next action: if local work needs reference cards or helpers, define and gate a
versioned whole-bundle manifest rather than assuming upstream fan-out supplies
that abstraction; re-check upstream before implementation because it is active.

## SkillOpt Verus Failure-Driven Idea Discovery (2026-08-21)

The current failure evidence does not support a whole-document SkillOpt router:
across nine historical monolithic candidates, the selection oracle union is
15/20, exactly the best fixed candidate. Cross-model trajectories instead show
that whole-skill outcomes confound invalid infrastructure, local action
validity, actor adoption, and exposure-induced proof-search drift. The
inspected test-20 is now diagnostic-only and cannot be used for method
selection or confirmation.

The selected Phase-0 direction is V-FACE, a deliberately narrow prospective
evaluation/admission protocol for three frozen typed proof-action templates.
It separates Build-only forced-edit technical validity, randomized card
exposure ITT, and adoption telemetry. Independent novelty review rated the
only plausible method increment PARTIAL, and four method reviews ended at
8.00/10 with the design frozen but the empirical verdict still REVISE.

Three offline pilots found zero whole-skill routing headroom, 532.94x
structured trace compaction with complete required-ledger coverage, and only
1/8 mechanically extractable near-miss lemma contrasts. The last result makes
the typed action compiler the hard gate. Next action is R001-R005 only:
inventory/contamination audit and a 30-checkpoint CPU compiler gate. Do not
implement runtime retrieval or claim solved-rate/token gains before that gate.

Canonical entry:
`research_memory/projects/verus_self_evolving/ideas/20260821-213956-skillopt-verus-failure-driven-v-face/ENTRY.md`.

## SkillOpt on VeruSAGE Feasibility Proposal (2026-08-06)

### Fixed Claude-stratified AC/AL/IR split (2026-08-14)

A new reference-free split is frozen at 40 train / 20 selection / 20 test for
the next SkillOpt experiments. It uses public VeruSAGE-Bench AC, AL, and IR
tasks and excludes 84 tasks from the previous SkillOpt-100 split plus 28 R040
tasks. Every split is exactly 25% historical Claude `FAILED/TIMEOUT` and 75%
historical Claude `VERIFIED`; train has AC/AL/IR counts 12/14/14, while both
selection and test use 6/7/7. Within each project/outcome stratum, source LoC,
historical runtime, and historical tokens define a deterministic joint
difficulty proxy with matched 2:1:1 assignment.

All 143 post-exclusion candidates matched the corresponding Claude historical
input after removing only the harness-injected loop-isolation attribute, and
all 143 failed the current source Verus precheck as expected. The frozen 80
have unique task IDs and source hashes with zero exact cross-split overlap.
No reference proof was exported, raw data remained read-only, and sealed MA/NR
directories were not read. Historical Claude outcome is a difficulty label,
not a claim about another actor's capability. The split remains task-held-out,
not project-held-out, because AC/AL/IR occur in every partition. Next action:
review the task list before pointing a live SkillOpt config at the new split.

Canonical artifacts:

- `skillopt-verusage/refine-logs/FIXED_CLAUDE_STRATIFIED_SPLIT_20260814.md`
- `research_memory/projects/verus_self_evolving/experiments/20260814-010634-fixed-claude-stratified-ac-al-ir-split/ENTRY.md`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-claude-stratified-80-seed20260814/`

### DeepSeek V4 Pro fixed-80 epoch 1 launch (2026-08-17)

A one-epoch aligned SkillOpt run is prepared on the new frozen 40 train / 20
selection / 20 test AC/AL/IR split. An independent GPT-5.6 Sol prelaunch review
confirmed that the actor call graph is Codex CLI native Responses, not the
legacy VeruSAGE actor pipeline, and that the configured roles are DeepSeek V4
Pro actor plus local GPT-5.6 Sol optimizer. The initial review nevertheless
returned FAIL/no-go, so no paid request or rollout was launched.

DeepSeek's 2026-08-16 peak/off-peak price change is now reflected in the
bridge and cost ledger. The previous aligned Pro actor token mix reprices to
USD 11.84 off-peak or USD 23.68 peak; the new-split planning range is USD
12-16 if completed off-peak. Per-request UTC times, price bands, and costs are
recorded, with boundary-crossing requests conservatively priced at peak. The
review found that native incomplete/error states, unsolved timeouts, hidden
optimizer retries, in-flight requests, and no-patch/identical candidates could
invalidate results or cost accounting. The integration now fails closed on
provider/model/terminal errors, retries unsolved tasks at 1,200/2,400/3,600
seconds, records every actor and optimizer attempt, drains the bridge, and
requires a fresh root, distinct S1, exactly 20/40/20 current actor results, one
strict gate decision, no test run, and complete accounting. The updated suite
passes 50 tests, compileall, shell syntax, targeted mypy, and offline 40/20/20
validation.

The ignored local `.env` now contains the key, but the launch script exposes it
only to the bridge child and removes it before actor/optimizer subprocesses.
The frozen split remains valid for same-family task-held-out evaluation; AC has
near-duplicate contexts across splits, so it cannot support project-transfer
claims. Next action is an independent remediation re-review, followed only on
PASS by a separate minimal live preflight and then the formal epoch. Both gates
passed: the preflight solved with V2 fidelity, exact `deepseek-v4-pro` response,
31/31 metered calls, zero errors, and USD 0.068973 off-peak cost. The formal
20/40/20 epoch launched at 23:15:29 UTC in tmux session
`skillopt-pro-fixed80-e1-20260817`. That 1,200/2,400/3,600-second run was
paused during S0 at 18/20 final results after two unsolved tasks entered their
second attempts; its trainer and both task trees remain stopped and its bridge
is idle.

A clean replacement Epoch 1 ran from 00:16:07 to about 00:56 UTC on 2026-08-18
with a fixed 600-second actor budget. Valid `V1_TRUNCATED` budget exhaustion
was judged once and was not retried; `V0_INVALID` infrastructure failure
retained two fresh retries. The actor/optimizer roles, frozen split, initial
skill, 20/40/20 schedule, 40-worker cap, strict gate, and no-test contract were
unchanged. Only one epoch was configured, so no later epoch could begin after
the 01:00 UTC peak-price boundary. S0 solved 13/20, training solved 23/40, and
S1 solved 14/20; the +1 paired-selection gate therefore accepted the candidate.
The actor ledger records 2,156 metered requests, all off-peak, 98,624,902 prompt
tokens, 2,354,039 completion tokens, and USD 8.035293 known cost. One additional
CloudFront 502 request has unknown usage and cost. The local-quota optimizer
completed 9/10 logical calls; one analyst call failed after three attempts
because its 1,103,911-character input exceeded the 1,048,576-character limit.
Formal validation is therefore `fail` only on incomplete actor/optimizer
accounting, despite the exact 20/40/20 schedule and accepted performance gate.
On the matched selection set, S1 cost USD 1.844379 versus S0 USD 1.722547
(+7.1%) and used 20.874M versus 20.257M prompt-plus-completion tokens (+3.0%).
The accepted skill improved solved count but is not evidence of token savings.

Durable entry:

- `research_memory/projects/verus_self_evolving/experiments/20260817-140332-skillopt-deepseek-v4-pro-fixed-80-epoch-1/ENTRY.md`
- `research_memory/projects/verus_self_evolving/experiments/20260817-140332-skillopt-deepseek-v4-pro-fixed-80-epoch-1/PRELAUNCH_AUDIT.md`
- intended run directory:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-20260817`
- active 600-second replacement:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916`

Epoch 2 ran from `2026-08-18T04:01:00Z` to `04:48:23Z`, entirely off-peak. Its
training rollout solved 27/40, but the 3,947-byte candidate solved only 12/20
on selection versus the accepted skill's 14/20, so the main gate rejected it
and retained the Epoch-1 best skill. Epoch 2 then spent 40 additional actor
rollouts on longitudinal slow update. The previous/current skills in those
rollouts had the same SHA-256, both solved 12/20, and produced 12 stable
successes plus 8 persistent failures with no improvement or regression. The
slow-update optimizer prompt was 1,899,944 characters against a 1,048,576
limit; three identical retries failed, no guidance or slow candidate was
created, and the 20-task slow gate did not run. This reveals two pre-Epoch-3
blockers: skip longitudinal actor comparison when the two skill hashes are
identical, and compact optimizer input before retrying an oversized prompt.

A post-run optimizer audit distinguishes the main per-epoch update from the
longitudinal slow update. Epoch 1's main update produced five of six analyst
patches; one eight-failure minibatch exceeded the Codex character limit at
1,103,911 characters. The remaining merge/ranking pipeline completed, its
candidate was coherent, and the selection gate accepted it at 14/20 versus
13/20, but the trace summary was not complete. Epoch 2's main update completed
all six analyst, three merge, and one ranking calls, but its rejected candidate
contains a sentence split by a misplaced `insert_after` edit, so call
completion does not imply artifact quality. Epoch 2's separate slow update did
not produce any summary or candidate because of the 1,899,944-character input.

A minimal slow-update input mitigation is now implemented without changing the
20-pair comparison, categories, ordering, inline metadata, optimizer prompt
structure, or output schema. Only the three trajectory-bearing pairs with the
largest combined previous/current bodies are replaced by two read-only paths;
all other trajectory handling is unchanged. Rebuilding the exact Epoch-2 Codex
input selects task IDs `f965b40cb14d9efe34f3`, `262a070f48e88a320e0c`, and
`d61c17b4662ca6d9cd58` and reduces the prompt from 1,899,944 to 921,083
characters, leaving 127,493 characters below the hard limit. No optimizer call
or actor rollout had been rerun at that point.

The compacted Epoch-2 slow optimizer retry subsequently completed at
`2026-08-18T07:40:38Z` in 214 seconds using one local GPT-5.6 Sol call. It used
1,721,649 prompt tokens and 7,532 completion tokens after the Codex agent read
the referenced traces; it made no actor call. The output was complete and
trace-grounded. It identified terminal wrapper/dependency failures, the Verus
`implies` quantifier-body rule, a concrete state-existential-to-`tla_exists`
bridge, bidirectional temporal-conjunction entailment, and decomposed
`init_invariant` preservation. Two recommendations are task-specific enough
that the result remains a candidate rather than accepted memory.

The candidate is scheduled for a strict 20-item selection gate with DeepSeek
V4 Pro through Codex CLI native Responses at `2026-08-18 05:01:00 CDT`
(`10:01:00Z`), immediately after the current peak-price window ends. A
persistent user-systemd timer launches a recoverable tmux run plus a one-minute
cost monitor. Only a hard-score improvement over the retained 14/20 skill can
modify the active skill. If that gate and all accounting/integrity checks pass,
the controller runs Epoch 3 and then Epoch 4, validating between them and
stopping after Epoch 4. Each follow-up epoch requires 100 actor tasks: 40 train,
20 main gate, 20 previous-skill comparison, 20 current-skill comparison, and
20 slow gate. No held-out test is included. Missing results, invalid fidelity,
empty slow guidance, a missing gate, or incomplete accounting stops the
continuation before the next epoch.

The one-shot timer fired at 05:01 CDT but the transient systemd service exited
before creating a run artifact because its minimal `PATH` could not execute the
Node-backed Codex CLI. It made no actor request and incurred no cost. The
launcher now propagates both the resolved Codex executable and its runtime
`PATH`; the same minimal-environment preflight passes. The continuation was
manually launched at 11:30:54 CDT, still off-peak. Its first active phase is the
20-item Epoch-2 slow-candidate selection gate; Epoch 3 has not started yet.

The retry candidate subsequently solved 12/20 versus the retained skill's
14/20 and was rejected. Its result-local usage estimate was USD 1.319029, while
the time-bounded raw bridge ledger records USD 1.533659; the latter is the
cost-accounting value used for per-epoch visualization. As
required, rejection did not stop iteration: Epoch 3 ran all 40 training tasks
and solved 26/40. That rollout added about USD 3.143122, bringing cumulative
known actor cost to USD 20.623842; all new requests remained off-peak and added
no provider error or unknown-cost request. Epoch-3 optimizer analysis is in
progress. Five of six analyst calls completed, while one failed after three
local retries because its 1,062,841-character input exceeded the 1,048,576
limit. The trainer can still construct a partial-evidence candidate, but the
continuation's integrity check will prevent Epoch 4 after Epoch 3 completes if
the failed optimizer attempts remain in the ledger.

Despite the missing analyst minibatch, the remaining Epoch-3 optimizer stages
produced a candidate that solved 15/20 on selection versus the retained
skill's 14/20. The strict gate accepted it as the new best (`step_0003`), while
the Epoch-3 training rollout had solved 26/40. The run then entered Epoch-3
longitudinal slow comparison: the previous skill completed its 20-item sample
at 14/20 and the current skill completed at 12/20. Paired outcomes were 12
stable successes, 2 regressions, 6 persistent failures, and no improvement.
This does not undo the fixed-selection acceptance, but it gives the Epoch-3
slow optimizer concrete regressions to analyze. That local GPT-5.6 Sol call was
completed and produced trace-grounded guidance, but its candidate solved only
13/20 on selection versus the active skill's 15/20 and was rejected. The
retained final skill is therefore the Epoch-3 main candidate at 15/20. Epoch 3
completed the exact 40 train + 20 main gate + 20 previous-skill comparison +
20 current-skill comparison + 20 slow gate schedule and cost USD 8.742646 in
actor calls. Including the preceding Epoch-2 slow retry gate, the continuation
cost USD 10.276305 and the cumulative known actor cost is USD 26.437997. All
continuation requests were off-peak and added no provider error or unmetered
request. The controller then stopped before Epoch 4 because the Epoch-3 analyst
overflow increased failed/unknown optimizer attempts; no Epoch-4 artifact or
actor call exists.

That stop was later remediated with a minimal main-Reflect input change: in
each analyst minibatch, only the three longest formatted trajectory bodies are
replaced by read-only `conversation.json` paths, while the skill, remaining
trajectories, grouping, prompt structure, and output schema remain unchanged.
The exact missing Epoch-3 failure group fell from 1,062,841 to 341,089 prompt
characters and completed successfully. Re-merging that repaired evidence
produced a 5,542-character candidate, but its validation gate scored 14/20
versus the retained 15/20 and rejected it. That separate repair gate cost USD
1.284483 and did not alter the canonical run checkpoint.

Epoch 4 then completed all 120 planned actor executions: 40 training, 20 main
gate, 20 slow previous, 20 slow current, and 20 slow gate. Training solved
25/40. All six main analyst groups, three merges, and one ranking call
completed without retry or overflow. The 5,903-byte main candidate scored
14/20 versus the retained 15/20, with zero gains and one regression, and was
rejected. Because that rejection left the accepted skill unchanged, the slow
previous/current skill files had the same SHA-256 and both paired rollouts
scored 15/20 with identical per-task outcomes; this is a stochastic
same-skill comparison, not evidence about a skill delta. The slow optimizer
still completed from the 20 trajectory pairs, but its 8,660-byte candidate
scored 13/20, with zero gains and two regressions, and was rejected. Final
best remains the Epoch-3 skill at 15/20 (SHA-256
`1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e`).

Epoch 4 used 2,544 metered actor requests, 107,164,439 prompt tokens,
2,383,989 completion tokens, and USD 8.921985, all off-peak with no new actor
error or unmetered request. Its 11 local-quota GPT-5.6 Sol optimizer calls all
succeeded and used 9,823,189 prompt plus 85,817 completion tokens. The
canonical actor ledger now totals USD 35.359983; including the separate repair
gate gives USD 36.644465 for the canonical run plus that repair validation.
No held-out test ran. A final launcher check initially raced bridge request
teardown after all results were written; post-run checks confirmed exact task
counts, runtime state, slow output, and unchanged historical accounting
caveats, and the launcher now polls bridge idle state for up to 30 seconds.
Next action is to audit why both E4 candidates had no selection gains and to
skip or redesign slow comparison when its two skill hashes are identical,
before spending on the held-out test.

A durable internal-review visualization now shows per-epoch actor tokens and
API cost alongside training, main-candidate, slow-candidate, and retained-best
hard solved rates. It uses raw bridge-ledger epoch boundaries and explicitly
labels the unequal schedules (E1=80 tasks, E2=100, E3/E4=120), so aggregate
token bars are not presented as per-task efficiency. Artifacts are under
`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/figures/epoch_token_performance/`.

A second, matched-set visualization is the appropriate cost comparison across
skills: it restricts S0 and E1--E4 to the exact same 20 main-selection task IDs
and excludes training, slow rollouts, optimizer calls, repair-only gates, and
test. S0/E1/E2/E3/E4 respectively used
20.257M/20.874M/22.690M/13.606M/18.247M actor tokens, cost USD
1.723/1.844/1.819/1.207/1.458, and solved 13/14/12/15/14 of 20. Thus E3 is the
lowest-cost and highest-scoring observed candidate on this fixed set, but one
stochastic realization per checkpoint does not establish a causal efficiency
improvement. The aggregate table, 100-row per-task table, reproducible script,
PNG, PDF, and visual-review note are under
`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/figures/fixed_selection_cost_performance/`.

An accepted-lineage audit confirms exactly two semantic updates on the main
skill path. E1 replaced two broad rules and appended two sections: contract-
first/quantifier discipline, extensional bridges, infrastructure-aware
diagnosis, and bounded iteration. It improved the historical fixed gate from
13/20 to 14/20; the sole U-to-S task was `a23a4969155913255f76`. The empty
post-E1 `SLOW_UPDATE` markers contain no guidance and are not a third update.
E3 inserted two sections, Task Boundary and Exact Quantifier and Higher-Order
Shapes, with no deletions. It improved the historical gate from the retained
14/20 to 15/20; the sole U-to-S task was `aded79905be896942897`. Failure
minibatch membership was reconstructed from the frozen train order and shuffle
seed, but the patch artifacts do not preserve phrase-to-task attribution.
Moreover, the fresh E3 slow comparison scored old S1 at 14/20 and new S2 at
12/20, so the mechanism-level matches are not evidence of stable causal gain.
The Chinese audit, exact edit artifacts, hashes, source-example tables, and
downstream paired outcomes are in `skill_evolution_lineage_zh.md` beside the
matched-set figure.

A fresh paired actor check ran the retained S2 skill on the same frozen
20-item selection set with the native Codex CLI harness, max reasoning,
20-worker phase concurrency, and a 600-second per-task endpoint. DeepSeek V4
Pro solved 15/20; local-quota GPT-5.6 Sol solved 17/20. Paired outcomes were 15
S-to-S, 2 Pro-U-to-Codex-S, 3 U-to-U, and 0 S-to-U. Pro had one normal failure
and four valid timeouts; Codex had the same normal failure and two valid
timeouts. Historical Claude-failed coverage was 2/5 versus 3/5. Pro used 338
off-peak requests, 12.700M total tokens, and USD 1.357109 with complete
accounting; Codex reported 8.620M input and 0.130M output tokens on local quota.
The user declined a Pro extended-time rerun, so this remains a time-censored
selection-set diagnostic rather than an unbounded or held-out comparison. All
20 source hashes remained unchanged and no test item was read. Durable entry:
`research_memory/projects/verus_self_evolving/experiments/20260818-153002-fixed-20-s2-deepseek-v4-pro-versus-codex-actor-comparison/ENTRY.md`.
Next action: do not rerun Pro; only predeclare a separate extended Codex check
if its two censored cases become decision-relevant.

A per-task early-termination audit explains much of the apparent inverse
cost/performance relation. Across the 80 matched selection executions, solved
tasks averaged 178.9 seconds and USD 0.0440, whereas unsolved tasks averaged
583.8 seconds and USD 0.1564. No solved task timed out; 23/25 unsolved tasks
did, and actor cost correlates 0.955 with wall time. From E2 to E3, however,
the three unsolved-to-solved transitions explain only USD 0.2734 (44.6%) of
the USD 0.6124 gate-cost decrease. Stable successes saved USD 0.1259 and
persistent failures USD 0.2132, so E3 also had cheaper trajectories without
binary outcome changes. The pattern is mechanically coupled to early stopping
and remains descriptive without repeated matched seeds.

Epoch 2 executed 100 actor tasks and cost USD 8.126399 incrementally: USD
2.557402 train, USD 1.819149 main gate, USD 1.756627 previous-skill slow
rollout, and USD 1.993222 current-skill slow rollout. It added 2,303 metered
requests, 96,069,157 prompt tokens, and 2,317,533 completion tokens, with no
new provider error or unknown-cost request. The two-epoch cumulative known
actor cost is USD 16.161692. Historical Epoch-1 accounting caveats remain, and
the failed slow optimizer call adds three unknown-usage local-quota attempts.
No held-out test has run.

Continuation artifacts:

- `skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e2_resume_600s.yaml`
- `skillopt-verusage/scripts/run_codex_pro_sol_fixed80_e2_resume_600s.sh`
- `skillopt-verusage/scripts/launch_codex_pro_sol_fixed80_e2_resume_600s.sh`
- `skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e3_resume_600s.yaml`
- `skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e4_resume_600s.yaml`
- `skillopt-verusage/scripts/run_codex_pro_sol_fixed80_e3_e4_600s.sh`
- `skillopt-verusage/scripts/launch_codex_pro_sol_fixed80_e3_e4_600s.sh`
- `skillopt-verusage/scripts/run_codex_pro_sol_fixed80_e4_after_reflect_repair_600s.sh`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/epoch4_after_reflect_repair_complete.json`

### DeepSeek V4 Pro native-Codex epoch 1 (2026-08-13)

One formal epoch completed on the unchanged frozen 40/20/40 split (SHA
`53059264e5d0458e1fc50a3c1786cbeac6c671aedf56dd71fb32843b24d2c553`).
The actor was `deepseek-v4-pro` through Codex CLI and native Responses at max
reasoning; the optimizer was local `gpt-5.6-sol` at the observed max reasoning
setting. The initial 838-byte skill scored 16/20 on selection, train rollout
scored 35/40, and the 2,932-byte candidate scored 17/20 on the same selection
set. The paired gate was +1 gained, 0 lost, 16 retained solved, and 3 retained
failed, so SkillOpt accepted the candidate.

The formal actor ledger recorded 3,559 requests, 197.107M input tokens
(194.614M cache hit), 2.986M output tokens, zero provider errors, and USD
4.387887398. The local optimizer used 9 calls and 992,796 tokens at zero
metered cash cost. All 80 final results completed with 77 V2, 3 V1, zero V0,
and unchanged inputs. No held-out test was run, so this is an accepted
selection-gate result rather than evidence of population solved-rate or token
efficiency improvement. Next, audit the gained task and selected edits before
deciding whether to run epoch 2 from the accepted candidate.

Durable summary:

- `skillopt-verusage/refine-logs/CODEX_PRO_0813_EPOCH1_RESULT_20260813.md`
- `skillopt-verusage/refine-logs/SKILLOPT_REPRODUCTION_SUMMARY_20260813.tex`
- `skillopt-verusage/refine-logs/SKILLOPT_REPRODUCTION_SUMMARY_20260813.pdf`
- `research_memory/projects/verus_self_evolving/experiments/20260813-160536-skillopt-deepseek-v4-pro-codex-epoch-1/ENTRY.md`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-0813-max-sol-e1-20260813`

### DeepSeek-V4-Flash epoch-1 implementation and result

The first executable adapter is now present under
`skillopt-verusage/src/skillopt_verusage/` without modifying the pinned
SkillOpt or external VeruSAGE checkouts. It includes a deterministic
Anvil/IronKV-only split freezer, a central DeepSeek skill-injection proxy with
per-attempt usage logging and a 12-request rollout cap, isolated VeruSAGE task
subprocesses, independent final Verus/Lynette judges, compact optimizer-visible
conversations, and a custom SkillOpt launcher. The frozen config is one epoch:
20 selection-baseline rollouts, 40 training rollouts, and 20 candidate-gate
rollouts; test evaluation is disabled and the epoch-1 slow update only injects
the upstream empty placeholder.

Model-free validation passed (3/3 standard-library unit tests, compileall, and
mypy). The frozen Anvil/IronKV-only 40/20/40 split has SHA
`53059264e5d0458e1fc50a3c1786cbeac6c671aedf56dd71fb32843b24d2c553`
and zero cross-split overlaps. The epoch used DeepSeek-V4-Flash thinking for
both target and optimizer and completed all 80 planned task rollouts: the
initial skill scored 0/20 on selection,
training solved 2/40, and the 6,882-byte candidate scored 0/20 on the same
selection split. The gate rejected the candidate and retained the initial
838-byte skill (SHA
`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`).
No held-out test rollout was run.

The main epoch issued 358 target requests and 8 optimizer requests. Target
usage was 1,594,615 prompt tokens (1,031,680 cache hit and 562,935 cache miss)
plus 2,312,040 completion tokens, costing USD 0.729071 at the recorded
DeepSeek-V4-Flash rates. Optimizer usage was 67,128 prompt plus 50,702
completion tokens; because the upstream optimizer tracker did not retain the
prompt cache split, the ledger conservatively treats all optimizer prompt
tokens as cache misses (USD 0.023594). The conservative main-run total is USD
0.752665; provider smoke and both preflights raise the all-in setup-plus-run
estimate to USD 0.758769. One target call had a transient connection error and
zero usage; the harness continued, and all 80 task ledgers completed.

Post-run integrity diagnosis invalidates the epoch as a target-capability or
skill-effectiveness estimate. Of 357 successful target HTTP calls, 187 ended
at exactly 8,192 completion tokens; 177/187 of those had empty final
`content`, and 191/357 successful calls had empty final content overall. At
least one exact-cap call affected 69/80 tasks, and the final call was
exact-cap for 55/80. The proxy did not record `finish_reason`, ignored each
VeruSAGE call site's requested output budget, forced every call to 8,192, and
enabled high thinking even for patch-generation calls. Logs contain 90
explicit `LLM returned empty response` events across 27 tasks.

The exploration budget was also not faithful to this VeruSAGE checkout. Its
CLI defaults to 20 repair steps, while the pilot used 4 plus a 12-request hard
cap; 68/80 tasks reached step 4 without full success, and one task hit the
request cap. No task reached the 1,800-second subprocess timeout. Moreover,
the optimizer-visible compact training conversations retained only the final
answer text, not `reasoning_content`; 65/108 retained assistant slots were
empty. The two strict training successes remain independently verified lower
bounds, but the failures, the 0/20 gates, and the rejected learned skill are
confounded by truncation and cannot support comparative claims.

Do not start epoch 2 or held-out testing. First correct the proxy and run a
small frozen calibration: restore 20 repair steps, raise/remove the request
cap, record `finish_reason` and requested/effective budgets, reject or retry
empty/length-limited responses, use a larger thinking budget for reasoning
calls, and use non-thinking generation for concrete action/patch calls. Only
after a calibration has zero silent truncations should the 40/20 epoch be
rerun.

Data-safety caveat: while auditing whether the historical sampled-100 could be
reused, a byte-count command accessed all 100 listed source paths, including
MA/NR paths. No source text was printed, exported, modified, or sent to a
model, but this planning turn therefore cannot claim zero sealed-byte reads.
The implemented split freezer rejects every directory except
`verified-anvil` and `verified-ironkv`; the sampled-100 is no longer an
eligible split source. The actual frozen split and live run read only
Anvil/IronKV inputs, wrote only below `VERUS_SKILL_RUN_ROOT`, and did not read
or modify sealed MA/NR data.

Canonical implementation:

- `skillopt-verusage/configs/verusage_deepseek_v4_flash_e1.yaml`
- `skillopt-verusage/src/skillopt_verusage/`
- `skillopt-verusage/tests/`
- `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER.md`

Microsoft SkillOpt was cloned as a clean, ignored upstream checkout at
`skillopt-verusage/SkillOpt/`, pinned to
`9639719632daecacd1baaa47fe781f3c0253600a`. Interface review found that its
research engine can drive VeruSAGE through a thin custom `EnvAdapter`, but the
default recipe must not be run unchanged: the native gate is scalar, while
this project needs safety-first solved-rate/cost ordering, and the default
slow-update path can force-inject ungated guidance.

The proposal was revised to preserve the paper-facing 40/20 mechanism while
controlling VeruSAGE cost: freeze 100 new tasks from the leakage-audited
Anvil/IronKV effective-train pool as 40 train / 20 selection / 40
task-held-out test after a fresh provenance and near-duplicate audit; run one
40-task step per epoch, reflection minibatch 8, textual learning rate 4 with
cosine decay, and gated 20-sample slow update.
The primary stage is two epochs with meta skill disabled because an epoch-2
meta artifact would not be consumed. A clean four-epoch run with meta enabled
is conditional on the two-epoch live gate.

The two-epoch SkillOpt core requires 280-340 target task rollouts; H0 and
one-shot test controls raise the complete matrix to 360-420 per target model.
The corresponding four-epoch matrix is 600-660. At four repair attempts,
nominal target calls are 2,880-3,360 for two epochs, with a hard transport cap
of 4,320-5,040 requests. The optimizer adds about 16-22 logical calls. Because
historical per-task agent-event logs have a 1.11 MB median and upstream
reflection does not truncate them, optimizer-visible traces must be compacted
to at most 8k tokens per task while full evidence remains external.

Using the audited GPT-5.5/high 100-task run only as a token/cost prior, the
two-epoch complete matrix projects to 274-375M raw target input and
2.75-3.75M target output tokens. With the historical cache profile, a
GPT-5.5 target + GPT-5.5 optimizer arm is about USD 317-425; with all target
input treated as cache miss it is USD 1,461-2,003 before long-context uplift.
A DeepSeek-V4-Pro target with the same GPT optimizer was projected at about
USD 20-29 if the historical cache profile transferred, or USD 129-180 with
all target input as cache miss. Those were pre-run projections for a different
model/optimizer pairing and are superseded for this Flash/Flash pilot by the
measured ledger above.

The completed pilot supports only mechanical feasibility and cost
measurement. It does not support an effectiveness claim: the candidate was
rejected, the evidence has V2 rather than V3 fidelity, and the 40-task
held-out test was not run. It is not R042 evidence and does not authorize
sealed MA/NR reads. The main project next action remains R041; the SkillOpt
workstream's next action is the small budget-policy diagnosis described above,
not an unchanged second epoch.

Canonical artifacts:

- `skillopt-verusage/refine-logs/EXPERIMENT_PLAN.md`
- `skillopt-verusage/refine-logs/EXPERIMENT_PLAN_20260806_035709.md`
- `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER.md`
- `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER_20260806_035709.md`
- `research_memory/projects/verus_self_evolving/ideas/20260806-022611-skillopt-on-verusage-feasibility-proposal/ENTRY.md`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/split-100-seed42-20260806`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-flash-e1-20260806`

Paper-cost audit: SkillOpt arXiv v2 Table 6 reports aggregate GPT-5.5/GPT-5.5
training totals of 213.8M, 21.4M, 20.8M, 188.2M, 23.2M, and 59.3M tokens for
SearchQA, SpreadsheetBench, OfficeQA, DocVQA, LiveMath, and ALFWorld. These are
whole-loop totals, not measured per-task target-rollout costs: they combine
target execution with optimizer reflection/merge/ranking and repeated
selection gates. Any per-task number obtained by dividing them by released
split counts is therefore an amortized system-cost estimate, not a provider
usage measurement for one rollout.

The paper uses four epochs and normally 40 training items per optimization
step. Its text says ALFWorld has 39 train / 140 selection / 134 test
environments, while the pinned repository's released paper manifest says
39 / 18 / 134. ALFWorld rollout-count derivations must retain this version
discrepancy rather than silently choosing one. These paper costs do not justify
using the upstream batch size or extrapolated per-task token averages for the
more expensive multi-call VeruSAGE repair harness.

### Robust DeepSeek epoch-1 rerun status (2026-08-10)

The original Flash epoch remains performance-invalid. A corrected 8-task
calibration completed 5/8 tasks with 267 result-accounted requests, zero silent
truncations, and USD 0.309593 target cost. Subsequent full-run variants were
retained but invalidated before a complete epoch: one used the wrong Python
environment, one exposed a two-hour task timeout, one exposed an unresolved
64K response truncation, and v4 was stopped during the initial selection
baseline after source audit showed that an exhausted 256K retry would be
misclassified as an ordinary hard failure.

The harness now fails closed. Length-limited responses escalate from 32K to
256K to 384K; provider timeouts retry the same output budget; response-level
exhaustion triggers up to two clean task requeues with all prior attempts kept
outside the fresh task workspace. Exhausted task retries produce `V0_INVALID`
and abort the phase with process-group cleanup rather than entering the SkillOpt
score as zero. Budget reservations wait when only in-flight concurrency fills
the USD 20 envelope and require approval when committed conservative exposure
itself would exceed the limit. Thirteen unit/fault-injection tests, compileall,
and mypy pass.

Rerun v5 completed all 80 task ledgers with a 60-worker pool and actual
phase-bounded concurrency of 20 baseline, 40 training, and 20 candidate gate.
The initial 838-byte skill solved 6/20 selection tasks, training rollouts solved
8/40, and the learned 10,322-byte candidate solved 4/20 on the same selection
set. The gate rejected the candidate. The validation-best artifact remains the
initial skill, SHA
`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`.
The post-epoch 891-byte slow-update placeholder is recorded as current runtime
state but is not validation-best or an accepted learned candidate.

The target issued 4,184 requests using 35,527,687 prompt tokens (27,766,272
cache hit and 7,761,415 cache miss) plus 14,402,537 completion tokens, costing
USD 5.197054. Seven optimizer calls used 112,988 prompt and 68,942 completion
tokens; conservatively treating all optimizer prompts as cache misses adds USD
0.035122, for a combined v5 estimate of USD 5.232176. The shared budget ledger
ended at USD 8.930733 measured prior-plus-target spend and USD 16.936133 after
adding USD 8.005400 of worst-case uncertain exposure from interrupted calls;
the uncertain amount is not a confirmed provider charge.

Integrity passed: 80/80 complete, zero `V0_INVALID`, zero task requeues, and
zero silent truncations. Thirty-four explicit length-limited responses and one
empty response were rejected and recovered; no 384K escalation or provider
error occurred. This is a valid negative epoch-1 result: the learned candidate
did not improve selection solved rate and regressed by two tasks. It is not
held-out test evidence and does not establish a general SkillOpt effect. Next,
audit the paired regressions and generated edits before considering a revised
optimizer/skill representation; do not start epoch 2 or held-out testing
without a new reviewed plan. All generated runs remain below
`VERUS_SKILL_RUN_ROOT`; raw and sealed datasets remained read-only.

#### Post-run failure diagnosis (2026-08-11)

The paired audit found 14 fail-to-fail, zero fail-to-pass, two pass-to-fail,
and four pass-to-pass transitions. The candidate gate used 1,461 requests,
15.127M prompt tokens, 4.297M completion tokens, and USD 1.707599, versus 837
requests, 6.238M prompt, 2.770M completion, and USD 0.970353 for the initial
skill. The exact McNemar p-value is 0.5, so 20 tasks cannot establish a
population-level regression, but this candidate clearly failed its gate and
increased selection cost by 76%.

One paired regression has a direct learned-guidance mechanism. The optimizer
inserted a false general `fold_left` identity; the target copied it almost
verbatim, turning a 3-request verified baseline into a 128-request Verus
failure. The 10,322-byte candidate also incorrectly treated calls to existing
trusted `external_body` helpers as bypasses, conflicted with the actual
Lynette contract, and contained mutually inconsistent advice. It grew 12.3x
from the 838-byte initial skill through two large append edits with no semantic
replay or contradiction gate.

DeepSeek-V4-Flash's 20%-30% baseline/train solve rate is consistent with a
target capability ceiling, but the stronger direct evidence is that the same
Flash model was unreliable in the harder optimizer role. The local one-step
epoch also cannot reuse its rejected-edit buffer: the buffer is populated only
after the sole step and reset at the next epoch, while meta skill was disabled.
Do not run epoch 2 unchanged. First re-optimize the stored 40 trajectories with
a stronger optimizer, enforce compact atomic edits plus semantic/contract
linting, and pair one initial-skill A/A repeat with one revised-candidate gate.
Keep the DeepSeek target fixed for this isolation test; only test a stronger
target if the stronger optimizer still cannot help it.

Canonical diagnosis:

- `research_memory/projects/verus_self_evolving/notes/20260811-000000-skillopt-deepseek-v4-flash-epoch1-failure-analysis/ENTRY.md`

#### Pro optimizer reanalysis and retrieval audit (2026-08-11)

The training launcher now keeps optimizer and target roles separate; previously
it hard-coded Flash for both roles, so a YAML-only Pro selection would not have
taken effect. Two offline `deepseek-v4-pro` analysis/critic passes were run over
the stored 40 training trajectories with no new target rollout. The provider
maximum 384K output cap was used rather than a lower artificial analysis cap.

Pro v1 used 118,424 prompt and 3,487 completion tokens for an estimated
USD 0.054548, but failed serialization and trusted-context semantics. After
adding an immutable benchmark contract and host lints, v2 used 120,165 prompt
and 6,642 completion tokens for USD 0.058050 and generated a 1,646-byte
candidate. It still falsely attributed a stored `Verus=false, Lynette=true`
failure to Lynette and generalized a recursive-unfolding rule from one failed
trajectory. The candidate was rejected before any target gate. A deterministic
evidence-label check now catches this class of contradiction; 20/20 tests,
compileall, and targeted mypy pass.

This establishes that the earlier optimizer token cap was not the main
bottleneck: Pro stopped after only 6,642 completion tokens across v2's two
calls despite the 384K ceiling. A stronger optimizer plus unlimited analysis
budget improves compactness, but does not replace typed evidence, deterministic
contract checks, or causal support.

Source audit also confirmed that the main SkillOpt engine has no runtime
retrieval: every rollout receives the whole `current_skill`. SkillOpt-Sleep's
optional `recall_k` is only training-time max-Jaccard recall over historical
task intents during nightly consolidation and defaults to zero. It is not
proof-state/card retrieval. The next reviewed pilot should therefore keep the
838-byte seed fixed and retrieve at most one replay-supported typed card per
valid Verus checkpoint, with abstention; Pro should propose/criticize cards
offline rather than write one monolithic global skill.

The two Pro passes add USD 0.112598. Confirmed estimated spend is now about
USD 9.078453 including the prior measured target ledger and v5 optimizer,
below the user's USD 20 approval threshold. The separate USD 8.005400
interrupted-call exposure remains unconfirmed; even a conservative sum is
about USD 17.083853. Raw and sealed data remained read-only, and all generated
run artifacts stayed below `VERUS_SKILL_RUN_ROOT`.

Canonical audit:

- `research_memory/projects/verus_self_evolving/notes/20260811-204930-skillopt-pro-reanalysis-and-retrieval-audit/ENTRY.md`

#### GPT-5.6 Sol native optimizer replay (2026-08-12)

The requested stronger-optimizer isolation is complete. It reused only robust
v5's completed 40-task training rollout and ran the original SkillOpt
reflection, merge, ranking, and patch-application stages through local Codex
GPT-5.6 Sol. Five analyst calls, two merge calls, and one L=3 ranking call used
246,313 prompt and 11,184 completion tokens from local Codex quota. No metered
optimizer API dollar cost was incurred. The initial four-edit update was 4,109
bytes, so the host reran native ranking at L=3 rather than manually changing
model output. The final 3,490-byte candidate passed automatic and manual
contract audit.

The candidate nevertheless failed the same frozen 20-task DeepSeek-V4-Flash
selection gate: 4/20 versus the 838-byte S0 baseline's 6/20. Paired transitions
were 14 fail-to-fail, zero fail-to-pass, two pass-to-fail, and four
pass-to-pass. The two regressions finished Lynette-safe but Verus-invalid, so
they are proof-search regressions rather than executable-safety failures. With
no fresh S0 A/A repeat, target stochasticity remains a causal confounder; do
not attribute both regressions entirely to the skill.

The gate made 1,627 requests and used 12,924,510 prompt tokens (9,559,168 cache
hit; 3,365,342 cache miss) plus 5,446,664 completion tokens for USD 2.022979.
All 20 results were `V2_TRACE`. Thirteen length-limited and one empty response
were explicitly rejected and recovered; silent truncations, invalid tasks,
uncertain spend, and remaining reservations were all zero. Confirmed estimated
DeepSeek spend is now about USD 11.101432; including earlier worst-case
interrupted-call exposure, the conservative total is USD 19.106832, below the
user's USD 20 approval threshold.

This is a valid negative selection result, not held-out-test evidence. A
stronger optimizer repaired the obvious semantic and size defects of the
Flash-generated skill but did not make monolithic global-skill expansion
effective. Keep S0 as validation-best. Do not run epoch 2 or the 40-task test.
The next reviewed pilot should first measure S0 A/A variability and then test
typed, replay-supported, proof-state-conditioned retrieval cards with
abstention.

Canonical experiment entry:

- `research_memory/projects/verus_self_evolving/experiments/20260812-000000-skillopt-gpt56sol-native-replay/ENTRY.md`

#### Weekly closeout and Git publication audit (2026-08-12)

The 2026-08-10 through 2026-08-12 SkillOpt text update is complete. It records
the robust Flash epoch, paired failure mechanism, Pro offline reanalysis,
retrieval boundary, GPT-5.6 Sol native replay, cumulative cost boundary, and
the next S0 A/A plus typed-card retrieval experiment. The compact update is
`refine-logs/WEEKLY_MEETING_BRIEF_20260812.md`.

Git/GitHub publication did not track the research milestones. GitHub `main`
still ends at `deefdab` from 2026-07-26 UTC; local `main` has two unpublished
2026-07-26 commits but no commit dated this week. The parent repository still
sees `skillopt-verusage/` and the new SkillOpt memory entries as untracked.
Because the worktree also contains substantial older mixed changes, do not use
bulk staging. Branch creation, staging, commit, and push remain pending explicit
authorization and a confirmed path-level scope. The proposed recovery commits
are dated in their message bodies by evidence-backed milestone day
(2026-08-06 integration, 2026-08-10 robust epoch, 2026-08-11 Pro audit, and
2026-08-12 Codex replay) while retaining the real Git commit timestamp; do not
backdate repository history.

Canonical audit:

- `research_memory/projects/verus_self_evolving/notes/20260812-233707-weekly-skillopt-update-and-git-publication-audit/ENTRY.md`

#### Next model and retrieval configuration decision (2026-08-13)

Do not run another unchanged global-skill epoch. The selected next branch uses
the stored 40 Flash trajectories, GPT-5.6 Sol/high as an offline typed-card
proposer/critic, top-1 proof-state retrieval with abstention, and a bounded
DeepSeek-V4-Pro calibration followed by a fresh paired 20-task S0 versus
retrieval gate. This changes both the learned unit and runtime routing while
keeping the strongest optimizer already tested.

The planning budget is USD 10-12 of new Pro target spend for an 8-task
calibration plus 20+20 paired gate, with zero metered optimizer dollars through
the current local Codex quota or about USD 1.57 Sol API-equivalent. A full
80-task cycle would be approximately USD 5.2 with Flash, USD 16.0 with Pro, or
USD 70-90 with a GPT-5.6 Sol target under the historical GPT behavioral prior.
The earlier USD 20 approval envelope is nearly exhausted under the conservative
ledger and is not authorization for this new pilot.

Canonical decision:

- `research_memory/projects/verus_self_evolving/decisions/20260813-012036-skillopt-next-model-and-retrieval-configuration/ENTRY.md`

#### Codex target-harness alignment correction (2026-08-13)

The user clarified that future SkillOpt target rollouts and gates must use the
Codex hands-off harness aligned with the SkillOpt evaluation contract. The
external `autoverus/verusage` Verus Copilot scaffold with a DeepSeek proxy is
not the intended target harness. Use
`skill-evolution-pilot/src/skill_evolution_pilot/codex_runner.py` as the
implementation reference: fresh ephemeral Codex session, isolated workspace,
optional exact `SKILL.md`, local Verus/Lynette tools, complete event and usage
capture, and independent final validation.

S0, training rollout, candidate/retrieval gate, and any later held-out arm must
keep that Codex target contract fixed; only the skill condition may differ.
GPT-5.6 Sol remains the separate optimizer inserted after the first rollout.
The active DeepSeek-V4-Pro paired run may finish under its existing USD 12 cap,
but is now classified only as a harness-mismatch diagnostic and cost/capability
control. It is not the aligned SkillOpt reproduction and cannot authorize a
second epoch or held-out effectiveness claim.

Canonical correction:

- `research_memory/projects/verus_self_evolving/decisions/20260813-035234-skillopt-codex-harness-alignment/ENTRY.md`

The user then froze the next execution order: after the active mismatched Pro
batch finishes, run SkillOpt with DeepSeek-V4-Flash as the actor through the
Codex CLI hands-off target harness and GPT-5.6 Sol/high as the optimizer. Run
one 40-train/20-selection epoch first. Continue one epoch at a time only after
the native hard gate strictly improves the accepted selection score; stop on a
tie or rejection, and do not exceed four total epochs without a new decision.
The executable handoff prompt is:

- `skillopt-verusage/refine-logs/EXECUTION_PROMPT_CODEX_FLASH_SKILLOPT_20260813.md`

Codex CLI custom providers currently require a Responses-compatible wire API,
whereas the existing DeepSeek integration is Chat-Completions-compatible. The
next agent must validate a minimal protocol bridge with real Codex tool calls
before live rollout. It may not fall back to GitHub Copilot CLI, VeruSAGE, or
direct one-shot generation and still call the experiment aligned.

Core hypothesis:

> Historical Verus repair traces can be compressed into verifier-grounded
> prompts or skills that preserve hands-off-level solved rate while reducing
> uncached inference tokens, wall time, or required model scale. Promotion
> requires project-held-out live reruns; offline information gain alone is
> insufficient.

## Codex Sampled-100 Cost Audit (2026-08-06)

The completed GPT-5.5/high H0 rerun on 100 sampled tasks solved 77/100 under
the strict joint Verus/Lynette criterion. Thirteen runs timed out, and those
same 13 lack terminal usage. Exact observed usage over the other 87 is
66,264,870 raw input, including 61,448,832 cached input, plus 665,288 output
tokens; reasoning output is 259,838 and is a subset of output.

At current standard GPT-5.5 API-equivalent rates, the observed-87 lower bound
is USD 74.76. Mean and duration-matched projections put the complete 100-task
batch at about 76.2-89.4 million raw input, 0.765-0.892 million output, and USD
85.93-98.07 before any long-context uplift. These are counterfactual API
prices, not the Codex subscription invoice; exact timeout usage and
per-request long-context eligibility are unrecoverable from the terminal-only
CLI stream.

Among terminal-usage-complete runs, strict successes average 60,840 primary
uncached tokens and USD 0.792 API-equivalent cost, while failures average
77,955 and USD 1.322. Because usage is missing for 12/23 failures but only
1/77 successes, duration-matched estimates are more appropriate for the full
groups: about 61,377 tokens / USD 0.805 per success and 90,590 / USD 1.567 per
failure. The frozen 600-second cap applies to the Codex subprocess; independent
Verus and Lynette checks occur afterward with separate caps of up to 120
seconds each, so total recorded wall time can exceed ten minutes.

Canonical audit:

- `research_memory/projects/verus_self_evolving/notes/20260806-030457-codex-gpt-5-5-sampled-100-token-cost-and-success-audit/ENTRY.md`

## Verus Retrieval Skill-System Design (2026-08-04)

Per-file memory extraction is a useful ingestion/cache boundary, but free-text
file summaries should not be the primary retrieval unit. Static knowledge
should be indexed at declaration, specification, proof-block, and dependency
edge granularity. Exact symbol lookup, sparse lexical search, scope/type/mode
filters, dependency traversal, structural proof-state matching, metadata
facets, verifier-transition matching, and iterative error-driven requery are
all first-class channels; embeddings are optional supplementary recall.

This static Verus hybrid retriever is a useful substrate and strong baseline,
not a complete skill system or a sufficient research novelty. RAG-Verus,
KVerus, LeanDojo/ReProver, Rango, and graph premise-selection work already
cover much of repository metadata, dependency-aware premise retrieval,
evolving-state retrieval, and verifier-driven refinement.

The smallest implementation-ready research mechanism is
`replay-validated selective lemma-transition retrieval`: within one frozen
repository/version/error family, an exact single-edit `invoke_lemma` action
becomes retrieval-eligible only after same-state replay reproduces its Verus
improvement, type/scope/mode and Lynette checks pass, and task-disjoint
validation does not show harm; otherwise the router abstains. The first
10-20-operator/state pilot is a kill gate, not a population-effect or
cross-project claim.

Active caveat: R041 H2 remains a negative qualitative candidate, not evidence
that global memory generally harms agents or that transition retrieval works;
the three-case sample is selected and the Qwen verifier-access confound remains.

Next action: enumerate and replay exact single-edit lemma transitions before
building a broad memory taxonomy. Canonical design:

- `refine-logs/FINAL_PROPOSAL.md`
- `research_memory/projects/verus_self_evolving/ideas/20260804-174224-verus-retrieval-skill-system-design/ENTRY.md`

### Retrieval index, trigger, and card contract (2026-08-05)

The broad multi-index substrate has now been reduced to an
implementation-ready recall experiment. Files remain ingestion/invalidation
boundaries; retrieval units are typed symbols/specifications, dependency
edges, normalized verifier states, and replay-certified transitions.

For the first experiment, a frozen `B_train` bank contains only exact
single-edit `invoke_lemma` transition cards. Exact symbol, FTS5/BM25, and
analyzer-derived accessible dependency channels project explicitly to card
IDs. Cheap search runs invisibly after every valid candidate-hash-bound Verus
checkpoint; a separate deterministic policy injects at most one active,
type-valid, structurally anchored card or abstains.

Recall is leakage-safe and stage-attributed. `D_train` extracts shadow cards,
`D_val` alone promotes active cards and freezes all rules, and `D_eval` never
updates the system. The eval oracle contains only frozen train cards that
independently replay successfully on an eval pre-state. Report transfer
opportunity (`R-1`) before conditional index/search/filter/rank/injection/use
recall, so a nearly empty transferable-memory set cannot be hidden.

Failure routing separates `HARNESS_INVALID`,
`VERIFIER_RESOURCE_SYMPTOM`, and `SEMANTIC_PROOF_FAILURE`; missing verifier
feedback and raw resource symptoms do not directly trigger proof memory.
Filters are three-valued (`VALID / INVALID / UNKNOWN`), and unknown bindings
remain auditable but are not injectable.

Independent refinement converged from 6.38 to 7.69 to 9.06/10 (`READY`, no
blockers). This is implementation readiness only. It does not establish live
solved-rate or token-efficiency gain, and R042 remains incomplete.

Canonical design:

- `refine-logs/retrieval-trigger-design/FINAL_PROPOSAL.md`
- `refine-logs/retrieval-trigger-design/REVIEW_SUMMARY.md`
- `research_memory/projects/verus_self_evolving/ideas/20260805-141718-verus-retrieval-index-trigger-and-card-contract/ENTRY.md`

## Hands-Off Log Fidelity And Phase Segmentation (2026-07-25)

The earlier read-only analysis of the 30-trace R040 train selection was a
phase-segmentation pilot, not a corpus-wide log-fidelity audit. It suggests
using verifier checkpoints as macro boundaries, tool calls as micro-events,
edits as actions, and `verus-checker`/Lynette as separate safety validation.
This recommendation remains provisional until validated on a heterogeneous
full-corpus sample with explicit boundary labels.

The sample contains 24 plain CLI logs and 6 structured o4 JSONL logs. Tool/edit
sequences are detectable in 28/30 and explicit Verus invocations in 27/30;
summary-only and raw-diagnostic logs require provenance-aware fallbacks. In
the six exact JSONL logs, 55 Verus boundaries correspond to 46 single-edit,
5 multi-edit, and 4 zero-edit intervals, showing why edits and verifier calls
must not be treated as one-to-one.

The authoritative full audit covers 9,383 primary hands-off logs:

- 8,447 (90.0%) have tool-call markers, but only 859 (9.2%) have all started
  shell commands paired with uncompressed completed JSONL events.
- 60,581/75,904 (79.81%) successful Edit events retain exact line-level
  diffs. Among Edit events with displayed diff boxes, 60,581/60,740 (99.74%)
  match the declared line counts. It is therefore incorrect to characterize
  code edits as generally incomplete.
- The edit losses are format-specific: 15,164 successful Edit events are
  summary-only, all 5,977 UI Create events omit bodies, and all 4,000 o4
  `file_change` events omit patch text.
- 9,031/9,383 (96.3%) have paired original/final code, which recovers exact
  final net diff but not intermediate edit history.
- 735 (7.8%) have strict structured verifier trajectories and 3,259 (34.7%)
  have explicit verifier payloads.
- 0/9,383 expose thinking/reasoning-token fields. Usage is available in
  9,268 (98.8%), but visible narration and output usage are not hidden
  reasoning tokens.

Downstream analyses must separately label tool payload, exact diff, Create,
verifier payload, original/final pairing, and incremental replayability.
Verifier-anchored phases are exact only when both verifier evidence and the
evaluated code state are recoverable; otherwise they must carry a weaker
provenance label.

Canonical note:

- `research_memory/projects/verus_self_evolving/notes/20260724-165940-hands-off-verifier-anchored-phase-segmentation/ENTRY.md`
- `research_memory/projects/verus_self_evolving/notes/20260725-215004-full-hands-off-log-fidelity-audit-migration/ENTRY.md`
- `docs/hands_off_log_fidelity_audit.zh.md`
- `scripts/hands_off_log_fidelity/`

## Three-Objective Skill Evolution Pilot Design (2026-07-26)

The current draft intentionally separates three metric-overfit skill loops:
token cost, API small-model benefit, and pre/post full-proof InfoGain. All
three start from the same `n=4` fresh Codex H0 tasks but operate in isolated
workspaces. Each objective-specific meta-agent sees only its own traces,
primary metric, and safety evidence; one call analyzes the prior round and
emits three new skills.

For `n=4`, the first round requires 31 Codex agent invocations, 12 small-model
agentic trajectories, and 28 local teacher-forced scoring sequences. Later
rounds require 27, 12, and 24. A final frozen meta-skill synthesis adds three
Codex calls. If the API agent uses one model request per step with
`max_iters=10`, the 12 small-model trajectories can require up to 120 actual
API requests per round.

The four token-branch tasks are now fixed. The first three retain their
historical labels (stable pass, stable closest failure, unstable). The user
selected IronKV `delegation_map_v__impl4__range_consistent_impl` as the fourth
task. Contrary to the historical expectation, current Codex solved both its
standard source and the same-task no-lemma source under fresh H0. The standard
source is therefore labeled `hard_solved`, not `current_codex_failure`; this
negative screening result must remain visible.

Canonical draft:

- `research_memory/projects/verus_self_evolving/experiments/20260726-001827-three-objective-metric-overfit-skill-evolution-pilot/ENTRY.md`
- `skill-evolution-pilot/EXPERIMENT_PLAN.md`
- `skill-evolution-pilot/INFORMATION_CONTRACT.md`
- `skill-evolution-pilot/DEBUG_GATES.md`
- `skill-evolution-pilot/TRACKER.md`
- `figures/three-objective-skill-evolution-loop.mmd`
- `figures/three-objective-skill-evolution-loop.png`
- `figures/three-objective-figure-index.md`

The shared workflow figure was refreshed in English on 2026-07-29. It now
states the current task contract accurately: three shared comparison roles and
one branch-specific hard case. The figure index distinguishes completed token
plots from the completed-but-unplotted small-model R1 result and the
not-yet-complete InfoGain branch.

The pilot now has a staged launch contract. Token cost is the first executable
branch. Before any metric experiment, model-free tests must validate the
normalized event schema and credential redaction; two fresh one-task Codex
H0 runs must then establish workspace visibility, edit/tool payload fidelity,
candidate-hash-bound verifier checkpoints, independent Verus/Lynette
validation, and token usage completeness.

OpenRouter `qwen/qwen3.6-27b` is the primary small-model transport. Its
credential is runtime-only through `OPENROUTER_API_KEY` and must never enter a
command, manifest, response log, exception, memory entry, or repository file.
The historical OpenRouter repair script is reference material only because it
does not satisfy the new isolation and logging contract. Local Qwen is a
separately labeled last-resort arm after a recorded no-credit or bounded
provider failure; API and local results cannot be pooled.

The minimal token engineering smoke requires six Codex invocations: two fresh
H0 runs on one task, one token meta-agent call producing three skills, and
three skill-conditioned solver runs. An optional reflection is a seventh call.
Only after this smoke is fully auditable should the project identify the fourth
task through an H0-only screen and launch the 12-run token first round.
InfoGain remains later because its full-proof target span and scorer contract
are not yet frozen.

The experiment-local infrastructure is now implemented below
`skill-evolution-pilot/src/skill_evolution_pilot/`; 28 model-free tests pass.
It retains complete raw provider/Codex fields, uses normalized events only as a
secondary index, redacts credentials, records visibility manifests, and saves
full candidate snapshots/diffs at every completed Codex tool/edit boundary.

Two real `gpt-5.6-sol/high` fidelity smokes used the prior stable-pass task
`seq_filter_contains_implies_seq_contains`; neither is the fourth task. Smoke
01 solved but failed F3 because the first adapter treated four valid
`todo_list` events as unknown. After the lossless mapping was added, smoke 02
passed F3: 25/25 raw events exactly indexed, six completed command/edit
boundaries covered by eight full candidate snapshots, zero missing/unpaired
payloads, zero truncation markers, zero shell-edit suspects, unchanged input,
and matching independent Verus/Lynette validation.

Smoke 02 recorded 232,495 input, 203,264 cached input, 1,671 output, and 369
reasoning-output tokens but no visible reasoning text. A follow-up audit showed
this was a harness omission: the local `gpt-5.6-sol` catalog supports reasoning
summaries but defaults to `summary=none`. Smokes 01-02 are therefore not
canonical final baselines.

Smoke 03 explicitly requested `model_reasoning_summary="detailed"`, forced
reasoning-summary support, disabled hiding, and enabled raw-reasoning display.
It passed F3 and returned four reasoning events with 186 total characters,
while usage reported 392 reasoning-output tokens. The exact returned events
are present in both raw and normalized logs. They are reasoning summaries, not
the entire hidden 392-token sequence. The harness now requests and preserves
all exposed reasoning fields but does not claim hidden chain-of-thought access.
Smoke 03 is the canonical Codex fidelity configuration.

The durable compact log is `skill-evolution-pilot/RUNLOG.md`; complete runs
remain outside the repository under `VERUS_SKILL_RUN_ROOT`.

Canonical H0 and token G6 execution are complete. The three historical tasks
were 3/3 solved and 3/3 F3 in the fresh canonical batch, with 25,555, 71,816,
and 32,784 primary uncached tokens. Two canonical stable-pass H0 runs have
mean 27,660 uncached tokens and 10.8% coefficient of variation.

The one-task token meta-agent emitted exactly three schema-valid skills. A
replayed visibility audit confirmed no access outside its allowlisted
workspace. On the stable-pass engineering smoke, H0, conservative,
aggressive, and structural conditions all solved and passed F3; their primary
uncached tokens were 25,555, 15,611, 20,320, and 28,880 respectively. These
single-task deltas (-38.9%, -20.5%, +13.0%) establish that the intervention is
measurable and produces useful contrast, not that token efficiency generally
improves.

The standard fourth task solved in 410.97 seconds using 79,245 primary
uncached tokens. Its no-lemma diagnostic also solved in 496.61 seconds using
81,130 primary uncached tokens. The standard version is frozen for the token
matrix. A first full-four meta-agent attempt was invalidated because it wrote
scratch evidence to `/tmp`; its logs were retained. The runner now forces
scratch storage inside the meta workspace and treats any outside path as an
invalid visibility audit. One isolated attempt then stalled before tool use
and was terminated. The next retry completed in 327.04 seconds with a valid
schema, zero outside-workspace commands, and zero secret matches. It emitted
`bounded-exploration-gate`, `delta-certificate`, and `obligation-graph`. The
frozen 3-skill x 4-task token matrix is now running with Codex concurrency 6
and a 600-second per-run cap.

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

## R041A And ATLAS Paired Completion (2026-07-22)

All current local Qwen batches are complete. R040B produced 30 H0 repair
trajectories on 30 unique calibration tasks; R040C added 18 H0 repetitions on
9 predeclared qualitative candidates; R041A added 18 H1/H2 trajectories on 3
H0-frozen cases. The ATLAS paired pilot added 8 Qwen trace diagnoses and 8
gpt-5.6-sol/high diagnoses on the same held-out failures. Therefore the current
Qwen execution total is 74 trace-conditioned calls: 66 repair trajectories and
8 ATLAS diagnoses, covering 38 distinct calibration/eval task traces. The
separate R041 distillation call consumed a packed set of 30 independent train
traces but is one global model call, not 30 repair trajectories.

R040B's unbiased screen result remains 7/30 security-valid solves, with 11
stalled, 10 timeout/infrastructure, and 2 unsafe outcomes. The selected R040C
repetitions completed 18/18 and supported freezing one 3/3 stable pass, one 3/3
stable localized closest failure, and one 2/3 unstable case. These selected
repetitions do not define a solve-rate estimate.

On the frozen three-case R041A diagnostic, H0 and length-matched generic H1
each passed 5/9, while trace-distilled H2 passed 4/9. H0 and H1 were Lynette-safe
in 9/9; H2 was safe in only 6/9. Recorded whole-session token totals were
3.503M for H0, 3.502M for H1, and 4.449M for H2. This is a negative qualitative
signal for the current H2 prompt: it neither improved passes nor reduced
observed inference cost and introduced three safety regressions. It is not a
held-out method-effect estimate, and the three cases were selected for
mechanism diagnosis rather than population inference.

The ATLAS pilot completed 8/8 valid diagnoses per model. Qwen and
gpt-5.6-sol/high agreed on the exact taxonomy code in 7/8 pairs. In blinded
quality review, Qwen scored 36/48 versus 45/48 for the frontier arm; Qwen had
slightly stronger evidence grounding (16 vs 15), while the frontier arm was
more root-cause-specific (14 vs 11) and actionable (16 vs 9), winning 7/8
pairs. There are no human gold diagnosis labels, the taxonomy was induced by
the frontier model, transports differ, and each arm has one repetition, so
this supports only a qualitative actionability gap, not accuracy or a pure
model-scale claim.

Next action: audit the completed R041A trajectories at the failure/edit level
before changing the prompt. Treat the current global H2 as a failed qualitative
candidate unless the audit identifies a narrow, testable construction bug.
For a stronger ATLAS claim, add expert adjudication or run three frozen
repetitions per arm to separate cross-model differences from within-model
variance. R042-R053 held-out live evaluation remains required for any
solved-rate or token-efficiency claim.

Canonical compact artifacts:

- `refine-logs/ATLAS_PAIRED_RESULTS.md`
- `refine-logs/EXPERIMENT_PLAN.md`
- `refine-logs/EXPERIMENT_TRACKER.md`
- `${VERUS_SKILL_RUN_ROOT}/r040b_qwen_screen_20260721_live_attempt2/`
- `${VERUS_SKILL_RUN_ROOT}/r040d_adaptive_cases_20260722_attempt1/`
- `${VERUS_SKILL_RUN_ROOT}/r041a_contrast_20260722_attempt1/`
- `${VERUS_SKILL_RUN_ROOT}/atlas_paired_eval_20260722_attempt1/`

Raw and sealed datasets remained read-only; all generated outputs stayed below
`VERUS_SKILL_RUN_ROOT`.

## Codex Three-Case Fresh Baseline (2026-07-22)

A programmatic local-Codex baseline is complete on the same three H0-frozen
R041A qualitative cases. Each `gpt-5.6-sol`/high run started only from the
canonical unverified source; no old trajectory, verified answer, H1/H2
rationale, or case label was visible. Detailed JSONL events and all tool logs
were preserved.

Codex passed 3/3: the stable-pass task in 27.2 seconds, the stable localized
closest failure in 279.6 seconds, and the unstable task in 37.9 seconds. All
three independent Verus checks reported `1 verified, 0 errors`, all three
Lynette comparisons passed, and all immutable inputs retained their frozen
hashes. The corresponding Qwen H0 repetitions were 3/3, 0/3, and 2/3, so the
useful qualitative result is that fresh Codex exploration completed the
localized proof that Qwen repeatedly approached but did not solve.

This is one Codex repetition per deliberately selected task, with different
transport and agent scaffolding, so it is not a population solve-rate estimate
or a pure model-size effect. Next, compare the recorded edit/error sequence on
the closest-failure task against its three Qwen H0 trajectories and the
trace-distilled H2 trajectories; use that comparison to identify whether H2
failed through generic over-conditioning, unsafe edits, or failure to expose
the specific eight-byte-prefix/extensionality subgoals.

Compact report:
`refine-logs/CODEX_THREE_CASE_BASELINE_20260722_222807.md`.
Canonical detailed logs:
`${VERUS_SKILL_RUN_ROOT}/codex_three_case_baseline_20260722_attempt1/`.

## Skill-Distillation Synthesis And Failure-Path Audit (2026-07-22)

The prior literature surveys and current experiments are now consolidated under
`skill-distillation-analysis/`. The reviewed pool separates 21 formally
accepted core papers from six arXiv/workshop frontier papers and records full
titles, authors, publication-time affiliations, links, skill representations,
validation mechanisms, and the specific innovation that supported acceptance.
The cross-paper conclusion is that strong accepted work changes at least one
of the learning unit, validation signal, or update mechanism; method-level
work in the crowded 2026 skill-learning space usually needs to change two.
Trajectory summarization alone is not a sufficient main contribution.

The closest-failure edit/error audit found a material harness confound. All
nine Qwen H0/H1/H2 agent logs for calibration
`099e5503300d7b344c40` contain rejected attempts to call the configured
absolute Verus path (`Permission denied and could not request permission from
user`), although the independent runner-side final Verus check remained
available. Codex had working Verus feedback from its first iteration, used
compiler hints to locate `lemma_auto_spec_u64_to_from_le_bytes`, and completed
the remaining offset-index extensional proof without a bypass. Qwen H2/1 did
identify the fixed-prefix/cancellation structure and temporarily reduced the
proof to one error, but ended with an illegal nested proof function and an
unsafe `external_body` helper.

Therefore Codex 1/1 versus Qwen 0/9 on this task is not a clean model-scale
comparison. It supports a qualitative difference in converting available
feedback into a safe supported proof, but verifier-feedback availability is a
first-order confound. The current global H2 remains a negative candidate:
4/9 passes versus 5/9 for H0/H1, higher observed session cost, and three
Lynette regressions. Do not expand it or start parametric distillation.

Immediate next action: create a workspace-local Verus wrapper or verified
safe PATH alias for the Qwen agent loop, require a command smoke that returns
real verifier stdout/stderr, then rerun the closest-failure H0/H1/H2 arms with
the same model, harness, timeout, and three repetitions. Only after that
matched control should the project test a minimal task-state-specific H3 with
negative scope (no `external_body`, no specification edits) and component
ablations. Treat information gain as a cheap prescreen only; promotion still
requires strict live verifier outcomes and Expected Cost to Success.

Compact artifacts:

- `skill-distillation-analysis/README.md`
- `skill-distillation-analysis/PAPER_MATRIX.md`
- `skill-distillation-analysis/FAILURE_PATH_ANALYSIS.md`
- `skill-distillation-analysis/RESEARCH_SYNTHESIS.md`

Raw and sealed datasets remained read-only. Full run logs remain only below
`${VERUS_SKILL_RUN_ROOT}`.

## Three-Objective Skill Evolution Execution Update (2026-07-26)

The frozen token first round is complete. All 12 skill-conditioned Codex runs
passed F3, Verus, and Lynette. H0 mean primary uncached Expected Tokens to
Success was 52,350. `bounded-exploration-gate` was best at 51,497 (-853,
-1.63%), `delta-certificate` was 53,794.25 (+1,444.25, +2.76%), and
`obligation-graph` was 52,418.5 (+68.5, +0.13%). Task-level interactions were
large, while the best aggregate gain is small relative to observed H0
variability. This is a valid contrast for meta-analysis, not evidence of a
general token-efficiency improvement.

OpenRouter is now operational through the runtime-only credential contract.
The final preflight returned the exact requested `qwen/qwen3.6-27b` identity,
a complete `READY` response, provider usage, and exposed reasoning counts. A
new host-controlled Qwen agentic runner then solved the stable-pass proof in
five API requests and 57.86 seconds. It performed real file reads, Verus
feedback, an exact code edit, and Lynette validation. The run passed F3 with
matching request counts and model identity, unchanged immutable input, and zero
credential matches. Complete sanitized provider payloads, tool payloads,
snapshots, and diffs remain under
`${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/qwen-agentic-smoke-20260726-openrouter/`.

The replacement NRKernel task
`impl_u__wrapped_token__impl1__lemma_interps_match_aux1` now has a complete
current-Codex screen. Codex used the full 600-second cap and remained
UNSOLVED; the run passed F3 with 165 raw events, 259 normalized events, 59
tool/edit boundaries, complete snapshots, unchanged input, and independent
Lynette success. Its final candidate still had a real Verus type error, so the
result is not an environment failure. This task is frozen as
`current_codex_failure` for the small-model branch; the completed token branch
retains its original hard-solved fourth task.

The isolated small-model meta-agent also passed its schema and visibility
audit. It saw only the four allowlisted Codex H0 evidence packs and the
small-model objective, emitted 73 normalized events, made no outside-workspace
commands, exposed no credential, and produced three skills:
`verus-ten-request-ladder`, `verus-lemma-first-minimal`, and
`verus-obligation-state-machine`. A matched OpenRouter Qwen H0 at
`temperature=0.2`, ten requests maximum, completed 4/4 with F3: two tasks
solved and two remained unsolved; NRKernel was UNSOLVED after ten requests and
447.9 seconds. One initial NRKernel transport attempt was discarded rather
than scored after a provider request remained incomplete.

The formal OpenRouter Qwen `3 x 4` first-round matrix completed below
`${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/qwen-small-model-r1-20260726/`.
All 12 trajectories passed F3 with no runner error or transport retry. Matched
H0 solved 2/4 tasks using 29 requests and 312,656 provider-reported tokens.
Every skill solved the identical two-task subset and failed the identical
closest-failure and NRKernel tasks: ladder 2/4, 32 requests, 354,570 tokens
(+13.41%); minimal 2/4, 30 requests, 327,572 tokens (+4.77%); structural 2/4,
29 requests, 355,616 tokens (+13.74%). Thus the first-round skills produced no
solve-rate improvement and increased total tokens. Provider cost was $0.1243
for H0, $0.1480 for ladder, $0.1170 for minimal, and $0.1780 for structural;
the minimal arm's lower dollar cost despite more tokens reflects token-type
pricing, not better solving.

Next action: do not promote any first-round skill as a small-model improvement.
Use the matched failure traces for a focused meta-analysis before deciding on
one additional iteration; the key question is why all three skills failed to
change the two hard-task outcomes. Start InfoGain only after its complete-proof
target span, truncation policy, and frozen scorer checks pass.

## Token-Cost Design Evolution R4-R6 (2026-07-27)

Three additional token-only evolution rounds tested the skill-expressible
agent-design hypotheses distilled from `tmp.txt`: minimal permanent guidance,
direct-first repair, compact planning, local context, differential diagnostics,
external verification, and conditional self-disable. Harness-level changes
such as provider caching, model routing, reasoning-effort routing, dynamic tool
schemas, and multi-agent parallelism were explicitly excluded. Each round used
one visibility-controlled Codex meta-agent, exactly three candidate skills, and
the same frozen four-task `3 x 4` matrix.

Strict results:

| Round | Best admissible skill | Solve rate | ETtS | Delta vs H0 |
|---|---|---:|---:|---:|
| H0 | no skill | 4/4 | 52,350.0 | - |
| R4 | `zero-ceremony-direct` | 4/4 | 59,032.0 | +6,682.0 (+12.76%) |
| R5 | `backward-contract-frontier` | 4/4 | 52,013.5 | -336.5 (-0.64%) |
| R6 | `micro-direct-kernel` | 4/4 | 51,881.0 | -469.0 (-0.90%) |

R6 reduced the four-task total from 209,400 to 207,524 primary uncached
tokens. Relative to H0, uncached input fell from 182,930 to 180,663 while
output increased from 26,470 to 26,861. Per-task effects remained
heterogeneous: R6 regressed the direct task by 5,585 tokens, improved the
closest task by 4,957, regressed the unstable task by 229, and improved the
hard task by 2,733. The result is therefore evidence for conditional routing,
not for a universally helpful injected workflow.

R6's aggressive `branch-certificate-cutoff` produced verifier-safe final code
on all four tasks and saved tokens on its three ledger-valid tasks, but its
closest-task run reached the 600-second boundary without a terminal usage
event. The strict matrix excludes that candidate. R6's best admissible result
also remains 384 tokens worse than the earlier R1
`bounded-exploration-gate` result of 51,497. All observed gains are single-run
pilot contrasts on evolution tasks and are small relative to measured H0
variance; they do not establish stable token efficiency or held-out
generalization.

One R6 orchestration race started two batch coordinators. The output-directory
guard prevented duplicate execution of any task: each of the 12 run
directories contains one trajectory. The strict summary was reconstructed
directly from the 12 independent ledgers rather than either partial batch
summary.

A separate canonical `gpt-5.5/high` logging diagnostic solved the stable-pass
task in 196.07 seconds and passed Verus, Lynette, and F3. It retained 100 raw
Codex events, 151 normalized events, 24 paired tool calls/results, 16 file
changes, 15 visible reasoning summaries, 32 candidate snapshots, terminal
usage, and zero secret matches. A lossless VeruSAGE-style transcript renderer
now preserves the readable trajectory plus exact embedded raw and normalized
JSONL. Hidden chain of thought was not exposed and is not claimed.

Next action: freeze R4-R6 as completed pilot evidence. Before another evolve
round, run matched repetitions of H0, R1 best, R5 best, and R6 best or build a
leakage-safe router with a genuinely held-out routing validation split. Do not
optimize further on the same four outcomes or call the 0.90% single-run delta a
stable improvement.

Compact artifact:
`skill-evolution-pilot/results/token_cost_r4_r6_summary.md`.
External detailed artifacts remain below
`${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/`.

## Token Evolution Visualization (2026-07-29)

The complete H0 plus R1-R6 token pilot is now visualized at task-skill
resolution. The main heatmap contains 76 cells: 19 conditions (H0 and three
skills in each of six rounds) by four frozen tasks. Successful ledger-complete
runs are colored by primary uncached token change against matched H0; failed
runs and runs missing terminal usage are explicitly hatched and are not
presented as token savings. A companion plot follows the best admissible skill
in each round.

The visualization makes the main limitation clear: skill effects are strongly
task-dependent and evolution is non-monotonic. R1 remains the best aggregate
single-run condition at ETtS 51,497 versus H0 52,350; R6 reaches 51,881, while
R2 and R4 regress to 58,832.25 and 59,032. The unstable task often benefits
from early-round skills, whereas the hard task regresses in R2-R4 and recovers
only in R5-R6. Because each task-condition has one trajectory, these are
descriptive pilot contrasts rather than uncertainty-calibrated efficiency
claims.

Reviewed artifacts:

- `figures/token_evolution_skill_heatmap.{pdf,svg,png}`
- `figures/token_evolution_round_best.{pdf,svg,png}`
- `figures/token_evolution_caption.md`
- `figures/token_evolution_figure_catalog.json`

The derived 76-row plotting table remains outside the repository under
`${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/visualizations/`; raw traces and
sealed data were not modified or copied. Next action remains matched
repetitions of H0, R1-best, R5-best, and R6-best, followed by leakage-safe
routing analysis if the task-specific effects replicate.

## Full-Proof InfoGain Status Correction (2026-07-29)

The earlier tracker and figure index incorrectly described InfoGain as blocked
before scorer execution. A read-only artifact audit shows that the frozen
Qwen scorer gate passed on all four complete reference proofs with exact,
non-truncated, reproducible teacher forcing. R1 and R2 each have 12 complete
F3+solved Codex trajectories, 12 paired pre/post scores, aggregate summaries,
and token-level scoring logs.

All three R1 post-summary means are positive (238.59, 402.57, and 435.24
bits); all three R2 post-summary means are also positive (165.27, 297.56, and
281.13 bits). The best normalized post score is R1
`minimal_sufficient_rationale` at 0.2198 bits per target token. R2 does not
improve on the strongest R1 result, so there is no monotonic evolution result.

R3 generated all 12 trajectories with 12/12 F3 and 11/12 solved. Its queued
scoring continuation launched on 2026-07-29 and produced 10/12 partial
pre/post token-file pairs, then stopped because the conservative hard-task run
did not contain the `last_message.txt` path expected by the scorer. No R3
aggregate summary exists. The partial scores are not used in formal
comparisons, and the R3 Codex trajectories do not need to be regenerated.
These scores remain secondary offline proxy evidence and do not establish
downstream solve-rate or token-efficiency gains.

## Small-Model And InfoGain Visualization (2026-07-30)

The two remaining objective branches now have task-skill heatmaps and
round-level summaries. The small-model audit includes H0 and all nine R1-R3
skills over four tasks (40 cells). Every complete condition solves the same
2/4 task subset. The round-best complete conditions use 312,656
provider-reported tokens for H0, 327,572 for R1, 321,998 for R2, and 322,195
for R3. Thus none improves solve rate or total provider-token use relative to
H0. One R2 condition and two R3 conditions have a hard-task runner error that
fails F3; those cells are hatched and excluded from aggregate token
comparison. Each task-condition has one trajectory, so all contrasts remain
descriptive.

The InfoGain heatmap includes all 24 exact R1/R2 task-skill scores and marks
all R3 cells pending. The strongest mean post-summary score is R1
`minimal_sufficient_rationale` at 0.2198 bits per target token; the R2 best is
`contract_unification_certificate` at 0.2031. The three-skill mean also falls
from 0.2149 in R1 to 0.1805 in R2. The completed rounds therefore show
positive post-summary likelihood shifts but no monotonic evolution. The
10/12 partial R3 pairs are explicitly excluded.

The matching pre-summary heatmap is now reviewed. It uses a diverging scale
centered on the per-task no-summary H0 reference at zero. Only R1
`dependency_bridge_map` has a positive four-task pre mean (+0.0705 bits per
target token); the other five complete skill means are negative. This does
not contradict the positive post results: pre scores skill text alone, while
post scores the terminal repair summary produced after solving.

Evaluator-side follow-up shows that the +0.0705 value is an unweighted
four-task macro mean, driven by the two marshal tasks (+0.1031 and +0.2901);
the direct task is +0.0154 and the long hard task remains -0.1265. Pooling all
9,354 reference-proof tokens instead gives -0.0587 bits per token, and
dropping the +0.2901 task makes the macro mean approximately zero (-0.0027).
Token-level comparisons indicate that the structural skill improves many
positions but that half of its positive advantage over the other R1 skills is
concentrated in roughly 2-3% of target tokens. The skill is not shorter than
the alternatives, and simple lexical overlap with evaluator-only proof edits
does not explain the result. The leading mechanism hypothesis is structural
priming: its representation-bridge, dependency-order, forward/converse, and
branch-assembly policy better predicts the two marshal proof shapes. This is
not causal evidence. A length-matched section-ablation/null-text scorer study
is required before attributing the gain to those semantics.

Reviewed artifacts:

- `figures/small_model_skill_heatmap.{pdf,svg,png}`
- `figures/small_model_round_summary.{pdf,svg,png}`
- `figures/infogain_skill_heatmap.{pdf,svg,png}`
- `figures/infogain_pre_skill_heatmap.{pdf,svg,png}`
- `figures/infogain_round_summary.{pdf,svg,png}`
- `figures/three-objective-figure-index.md`

The derived plotting tables remain outside the repository at
`${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/visualizations/three-objective-results-20260730/`.
Raw traces, sealed data, and partial scorer logs were not modified or copied.
Next action for this branch is to repair the R3 scorer input contract and
produce a complete exact aggregate before making any three-round InfoGain
comparison. No additional small-model evolve round should be promoted without
matched repetitions or a held-out evaluation split.

## Single-Problem Token-Cost Overfit Experiment (2026-07-30)

The intentionally overfit IronKV experiment on
`delegation_map_v__impl4__range_consistent_impl` is complete. It reused the
Token R6 Codex contract (`gpt-5.6-sol`/high, detailed exposed reasoning
summaries, 600-second cap), the R6 source identity, and the same Verus and
Lynette binaries. The user reduced each seed and per-round skill condition to
one solver trajectory; the completed design contains three fresh H0 runs,
three R6 seed runs, three rounds of three evolved skills, and three final
confirmation runs (18 solver trajectories total).

Fresh H0 was 3/3 verifier-safe and F3-valid with primary uncached tokens
82,779, 83,472, and 95,687: ETtS/mean 87,312.7, median 83,472, and range
12,908. The R6 seed skills did not improve H0: the best ledger-complete seed
was `micro-direct-kernel` at 100,365 (+14.95%). The
`typed-two-stage-oracle` seed reached the timeout without terminal usage and
is invalid for any token-improvement claim.

The best single-run screens were 70,308 for R1
`single-pass-dual-certificate` (-19.48%), 75,498 for R2
`witness-completeness-microcheck` (-13.53%), and 61,232 for R3
`local-proof-surface-cap` (-29.87%). The R3 candidate was selected for three
fresh confirmation runs. All three final runs passed Verus, Lynette, F3,
input immutability, and terminal-usage checks, using 68,303, 90,569, and
88,301 primary uncached tokens. Final ETtS was therefore 82,391, a favorable
delta of 4,921.7 tokens (-5.64%) versus fresh H0. Because that delta is
smaller than H0's own 12,908-token range, the predeclared conclusion is
`inconclusive_within_h0_range`, not a stable token-efficiency improvement.

One solver timeout/missing-usage run and two meta-agent timeouts without
schema output were retained as invalid evidence; valid meta outputs were
obtained for all three required rounds. The immutable source retained SHA-256
`24823fb931d96614653514129d1ca0e5fcec9347ed9600bb74d2fffe1f776264`.
No reference proof was visible to a solver or meta-agent, and only exposed
reasoning summaries were logged; hidden chain of thought is not claimed.
Legacy data remained read-only.

Canonical detailed artifact:
`${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/single-problem-token-evolve-delegation-map-20260730/`.
The reviewed summary figure is
`figures/single_problem_token_cost_overfit.{pdf,svg,png}`, with its caption,
catalog, and reproducible generator beside it under `figures/`. The derived
plotting table and figure manifest are stored under the canonical artifact's
`visualization/` directory. Visual review explicitly separated the
single-trajectory screening evidence from the three-run matched confirmation
and retained the `inconclusive_within_h0_range` conclusion.
The next evidence step, if this mechanism is pursued, is a larger matched
repetition set frozen before outcomes are viewed. Do not promote the skill or
claim cross-task generalization from this deliberately same-task overfit run.

## Self-Evolving Failure Mechanism Case Study (2026-08-04)

The completed negative results support a narrower architectural diagnosis:
the current loop is iterated monolithic prompt search, not cumulative
self-evolving memory. Each meta round consumes noisy whole-skill outcomes and
emits three complete replacement `SKILL.md` files. It has no clause/item
identity, parent-child edit lineage, local credit assignment, or runtime
retrieval. Useful rules can therefore be forgotten, harmful rules can
hitchhike with a selected skill, and screen winners can regress under fresh
confirmation.

The empirical pattern is consistent across branches. Token R1-R6 is
non-monotonic; no one of the 18 token skills improves all four task roles over
H0. The single-problem screen delta of -29.87% shrinks to -5.64% in
confirmation and remains within H0 variability. All complete small-model skill
conditions solve the same 2/4 subset as H0 while consuming more tokens.
Full-proof InfoGain also falls from R1 to R2 and remains a secondary,
non-causal proxy.

The next route should replace complete global skills with small versioned
proof-memory cards carrying state triggers, actions, negative scope, evidence,
matched token deltas, confidence, and deprecation status. A deterministic
retriever should select zero to three cards from the current proof state and
compile only those cards into the solver prompt. Each evolution step should
make one explicit operation (`ADD`, `STRENGTHEN`, `NARROW_SCOPE`, `SPLIT`,
`MERGE`, or `DEPRECATE`) with parent lineage and matched item-level
evaluation.

Canonical case study:

- `research_memory/projects/verus_self_evolving/notes/20260804-173507-self-evolving-failure-mechanism-case-study/ENTRY.md`

Do not launch another three-complete-skill rewrite round before testing the
matched H0 versus monolith versus retrieved-card versus oracle-retrieval
design on development and held-out task families.

## Standout Skill-Memory Case Study Shortlist (2026-08-05)

Six live-evaluated files are selected for mechanism case studies. The strongest
repeated same-task candidate is `local-proof-surface-cap`: its three-run
IronKV confirmation is 3/3 verifier-safe, with ETtS 82,391 versus H0
87,312.7 (-5.64%) and 30 versus 41 aggregate tool calls. The token delta
remains inside H0 variability and wall time does not improve, so this is a
mechanism case rather than a promotion result. The strongest cross-task
candidate is `bounded-exploration-gate`, with the lowest R1-R6 aggregate ETtS
at 51,497 versus H0 52,350 (-1.63%) and 4/4 solved; it helps two task roles and
harms two.

Four different task-state specialists achieve the lowest observed
verifier-safe token count for their respective role:

- `zero-ceremony-direct`: direct local proof, -23.24%;
- `local-contract-closure`: visible-contract closure, -43.49%;
- `typed-two-stage-oracle`: opaque typed API bridge, -18.58%;
- `batched-compiler-oracle`: hard IronKV branch/API search, -29.29%.

Their cross-task reversals make them evidence for state-conditioned retrieval,
not global prompt injection. `dependency_bridge_map` and
`minimal_sufficient_rationale` are retained only as pre/post InfoGain
organization exemplars. `three-fact-witness-note`, +37.02% on the same
single-problem R3 screen, is the matched negative comparator.

Canonical shortlist and exact file hashes:

- `research_memory/projects/verus_self_evolving/notes/20260805-135628-standout-skill-memory-case-study-shortlist/ENTRY.md`

Next action: extract small versioned cards from these six live skill files,
then evaluate a four-state router plus abstain against H0 and each monolithic
source with matched repetitions.

## Three-Metric Skill Case Study (2026-08-05)

A Chinese case-study report now separately audits token ETtS, small-model
verifier-safe solve rate, and pre/post InfoGain. The strongest same-round
contrast is IronKV R3-A `local-proof-surface-cap` versus R3-C
`three-fact-witness-note`: both are verifier-safe, but A uses 61,232 primary
uncached tokens, two solver Verus runs, zero new helpers, and 139 diff
additions; C uses 119,638 tokens, about six Verus runs, four helpers, and 302
additions. Both mention the same false-branch witness facts. The distinguishing
mechanism hypothesis is A's complete return-path ledger plus a hard initial
proof-surface cap.

R3-A's three-run confirmation remains inconclusive: ETtS 82,391 versus H0
87,312.7 (-5.64%), smaller than H0's 12,908-token range. The small-model
branch has no solve-rate winner; R2-C only reduces damage versus R2-A and
still costs 2.99% more than H0. A snapshot-derived audit finds 0.00 newly
declared proof-function helpers per trajectory for H0, R2-C, and R2-A; C
preserves the hard task's compiling 47-verified/1-logical-error state, whereas
A finishes compile-invalid. InfoGain has different phase winners:
R1-S is a marshal-driven pre structural proxy, while R1-C is a post-proof
compression proxy. R2 regressions do not support monotonic evolution.

An independent result-to-claim review agrees that the current loop generates
useful local mechanism hypotheses but has not established stable, cumulative,
or generalizable self-evolution. Next action: atom-level ablations on held-out
multi-branch tasks, host-enforced small-model rollback, and separate pre
retrieval from post writeback.

Canonical report and memory:

- `skill-evolution-pilot/results/three_metric_skill_case_study.zh.md`
- `skill-evolution-pilot/results/three_metric_skill_talk_notes.zh.md`
- `skill-evolution-pilot/results/three_metric_skill_talk_notes.en.md`
- `research_memory/projects/verus_self_evolving/notes/20260805-145000-three-metric-skill-case-study/ENTRY.md`
- `.aris/traces/result-to-claim/2026-08-05_run01/`

## SkillOpt Accepted-vs-Rejected Skill Case Study (2026-08-18)

A clause-level audit compared the two accepted main edits with E2/E4 main,
E2/E3/E4 slow, and E3 repair candidates. Accepted S2 contains short general
workflow rules plus reusable Verus motifs, but no named AC, AL, or IR proof
recipe. Rejected slow skills increasingly encode narrow temporal,
controller-transition, and infrastructure recipes.

The strongest retrieval signal is the rejected E2 slow candidate: it solved
`aded79905be896942897`, the same quantifier/higher-order case later gained by
accepted S2, but caused three retained successes to time out and scored 12/20.
Useful narrow knowledge therefore appears to create negative transfer when it
is injected unconditionally into the monolithic skill. All observed accepted
gains and rejected regressions crossed the 600-second timeout boundary, so
these one-rollout reused-selection results remain mechanism cases, not stable
causal solved-rate evidence.

Canonical note:
`research_memory/projects/verus_self_evolving/notes/20260818-161558-skillopt-accepted-versus-rejected-skill-case-study/ENTRY.md`.
The next design route is a short global core plus triggered, abstaining cards,
validated with clause-level matched multi-seed held-out comparisons.

## SkillOpt Non-Timeout Failure Audit (2026-08-19)

The fixed-80 actor outcome space intentionally includes valid unsolved
candidates as well as success and timeout: the actor may end after exhausting
useful approaches, and the host independently runs both Verus and Lynette.
Lynette was available and was invoked by the actor in every non-timeout
failure in the four main training and selection iterations.

The observed non-timeout failures are nevertheless mostly a harness defect.
Across the four main selection gates, 23/25 hard-unsolved executions timed out;
the other two were the same IR item, `cac8c7541d651d3480ff`. Across the four
main training rollouts, 45/59 hard-unsolved executions timed out and 14 ended
normally. Thirteen of those 14 came from eight IR tasks with the stale
`verus_builtin_macros` crate alias. Together with the selection item, nine
train/selection tasks cannot satisfy the current single-file Verus plus
Lynette joint contract: preserving the alias passes Lynette but fails before
Verus proof checking, while repairing it lets Verus run but Lynette correctly
rejects the executable delta. Only one main-training normal failure was a
clean early semantic stop, and it ended without an explicit final message.

The split precheck admitted the nine tasks because it treated every nonzero
Verus result as an expected unverified source; all nine have null verification
counts. The runner then labels complete terminal traces `V2_TRACE` independently
of proof success and always copies Verus output into `fail_reason`, even when
Lynette is the failing judge. The persistent invalid selection item does not
change paired gate deltas, but the eight invalid training traces contaminated
optimizer evidence and contributed infrastructure guidance to the accepted
Epoch-1 skill. Before another run or held-out test, require a real Verus summary,
resolve or invalidate the IR alias mismatch at the host layer, and separate
semantic, safety, infrastructure, timeout, and provider failure classes.

Canonical audit:
`research_memory/projects/verus_self_evolving/notes/20260819-190726-skillopt-non-timeout-failure-audit/ENTRY.md`.

## Blank/S2 Four-Model Baseline Audit (2026-08-19)

The planned held-out comparison is now four models crossed with two skill
inputs: a canonical empty Markdown control and accepted S2. The blank file is
one LF byte with SHA-256 `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b`.
Microsoft SkillOpt has no universal released initial skill; benchmark seeds are
task-specific, while upstream explicitly supports an empty skill. The prior
local 838-byte `initial.md` is a custom Verus seed and is excluded.

`Hands-off` was only an imprecise label for autonomous noninteractive Codex CLI
execution, not the legacy VeruSAGE `RepairRunner`. The label was removed.
Planned remote-provider groups now use 20 actor-task workers; local Qwen remains
at four to match vLLM's sequence capacity. Blank and S2 run sequentially inside
each provider group, so a provider does not receive 40 concurrent tasks. All
arms retain 262,144 context, max reasoning, 600 seconds, zero valid-timeout
retries, the same task prompt and verifier, and one exact skill file.

A same-family independent audit initially returned FAIL / NO-GO. It found that
the Chat bridge dropped Codex's custom `apply_patch`, direct and bridge invalid
accounting differed, GPT inherited unrelated credentials, and the test hash was
not enforced. These implementation defects are fixed and unit-tested. A real
Qwen blank-skill training smoke completed five `apply_patch` changes and seven
commands with no shell edits, unchanged input, F3 fidelity, and 12/12 completed
model requests. It ended unsolved as a valid 600-second timeout, so it is tool
compatibility evidence only, not a score.

Two frozen test items,
`f24cf9cc9db98c56f792` and `826687f9c56eb8e65d5d`, contain a stale
`verus_builtin_macros` alias and are not scoreable under the joint
Verus+Lynette contract. Raw data was not modified. By the 2026-08-20 experiment
decision, the original test-20 is retained: these items remain in all eight
conditions and count under the common solved/20 rule. The launcher and env
template now support `ZAI_API_KEY` plus the general
`https://api.z.ai/api/paas/v4` endpoint and explicitly export a sourced key to
the bridge. Current public Z.AI documentation lists `glm-5.1`, not the frozen
`glm-5.3` ID. A 2026-08-20 direct smoke confirmed that this account can call
the exact `glm-5.3` model through the general endpoint: HTTP success, no API
error, 20 prompt tokens, and 16 reasoning/completion tokens. The deliberately
tiny 16-token cap ended with `finish_reason=length` before visible answer text,
so this establishes model availability only. Estimated cost under the frozen
benchmark rates is USD 0.0000984.

A real GLM blank-skill Codex smoke then solved training item
`3a77a3e4e72edf600e2a` in 171.08 seconds: independent Verus and Lynette both
passed, all 24 metered requests completed with exact `glm-5.3`, usage was
312,922 prompt tokens (294,720 cached) plus 5,665 completion tokens, and
estimated API cost was USD 0.127036. Codex logged two transient 429 reconnect
events before a unique successful `turn.completed`; the F3 audit itself was
clean. The previous gate incorrectly treated every intermediate `error` event
as a failed terminal. It now preserves the error count but accepts a recovered
trace only when Codex exits zero with one completion, no `turn.failed`, a valid
provider ledger, and F3 audit. The stored trace reclassifies from its immutable
raw `V0_INVALID` result to `V2_TRACE` under the corrected rule. Qwen launch is
temporarily blocked because all four GPUs are occupied by another user's vLLM
workers; those processes were not modified.
Cross-provider request bytes and raw
tool schemas are inherently different, so future results may claim
semantic-contract controls, not strict
byte identity.

A follow-up artifact audit narrows the two IronKV failures and supersedes the
strong "not scoreable" interpretation above. The released unverified inputs
and their developer-written verified references both contain
`extern crate verus_builtin_macros as builtin_macros;`; the alias was not
introduced by an actor. The local evaluator uses Verus
`0.2025.07.12.0b6f3cb`, while the benchmark README recommends September 2025 or
later and the official reproduction instructions pin Verus commit
`ddc66116aa7a844a9e19cc50922fe85c84b8b4a5`. Both released references fail
under the local July binary at the alias import, so the observed compilation
failure is evidence of a local verifier-version mismatch, not by itself a bad
benchmark item. Deleting the alias is still an invalid candidate edit and is
correctly rejected by Lynette.

The released unverified/reference pairs also return `Files are different`
under the artifact's current Lynette binary in default, `-t`, and
`--asserts-anno` modes. The reference files contain a structurally different,
larger extraction and therefore are not directly input-aligned candidate
files. This does not establish that no legal proof exists, because evaluation
compares the unverified input against the actor's edited copy rather than
against the released reference file. Before excluding either item, replay an
input-aligned proof candidate with the officially pinned Verus and require
both successful verification and Lynette(input, candidate); until then report
these as incompatible with the current local toolchain, not inherently
unscoreable.

The official VeruSAGE Verus commit is now installed in the machine-local
side-by-side checkout recorded in `.agent-context.local.md`, without replacing
the July binary. The
checkout is exactly `ddc66116aa7a844a9e19cc50922fe85c84b8b4a5`; the built
binary reports `0.2025.09.11.ddc6611` and has SHA-256
`737048da2e41eabe9b3b0594edb11da6593358b8d55f8dcd270de539acd66e2d`.
Its vstd build verified 1,147 obligations with zero errors. Both disputed
released IronKV references now verify as `1 verified, 0 errors`; their exact
unverified inputs reach the intended proof failures instead of the missing
crate error, and Lynette accepts an unchanged input. One previously solved
GLM candidate also passes both the new Verus and Lynette. The ignored `.env`
now points `VERUS_BIN` at the official build and retains the old binary as
`VERUS_BIN_LEGACY`. Historical runs remain bound to their recorded July
binary; no past score is retroactively reclassified.

Canonical setup entry:

- `research_memory/projects/verus_self_evolving/experiments/20260819-170848-s2-skill-fixed-test-four-model-evaluation-setup/ENTRY.md`

Six formal arms are now complete. GPT blank/S2 scored 18/20 and 17/20,
DeepSeek V4 Pro scored 13/20 and 13/20, and GLM-5.3 scored 5/20 and 7/20. All
six arms have 20/20 provider-valid final results. Paired S2 deltas were -1, 0,
and +2, respectively; GLM's four gains were all historically normal items,
while its two regressions included one historical Claude failure. This single
test rollout does not establish a general S2 improvement.

Complete formal bridge-ledger spend was USD 2.991826 for DeepSeek and USD
3.241613 for GLM; GPT used local quota. Including GLM smokes and two rejected
pre-backoff concurrency attempts brings measured paid campaign spend to USD
7.449787. GLM required 739 internal HTTP-429 retries across its accepted arms.
Backoff recovered 20/20 provider-valid results, but blank/S2 had 16 and 12
timeouts, so 20 GLM workers exceeds effective account throughput. Qwen blank
and S2 remain blocked because another user's vLLM occupies all four target
GPUs. Next action: run Qwen at four workers after GPU release and calibrate a
lower GLM worker count before any scale-up.

That GLM calibration is now complete at two workers on four frozen-training
items. All four tasks produced one-attempt V2 traces; 51/51 upstream calls
completed with no HTTP-429 retry or backoff, three tasks solved, and measured
cost was USD 0.354103. The launcher now defaults GLM to two workers while
retaining four for other providers. Sequential blank/S2 GLM test-20 reruns at
two workers are in progress; the prior 5/20 and 7/20 worker-20 scores remain
throughput-confounded and must not be used as stable GLM capability results.

Both two-worker GLM reruns are now complete at 12/20 with 20/20 valid results,
so S2 has zero paired aggregate delta versus blank. Blank used 592 requests,
20,333,394 prompt tokens, 216,940 completion tokens, and USD 6.976968; S2 used
498 requests, 15,920,375 prompt tokens, 173,588 completion tokens, and USD
5.565405. Although every recorded upstream request completed without terminal
error, both runs still accumulated recovered HTTP-429 backoff. Lower local
concurrency removed the process/port conflict and greatly reduced timeouts,
but provider/account throttling remained. The stable pair cost USD 12.542373;
including prior formal arms, GLM smokes/rejected attempts, and the two-worker
calibration, measured paid campaign spend is USD 20.346263.

The DeepSeek selection uplift is confirmed as custom-S0 13/20 to retained-S2
15/20 on the reused selection set, but it is selected in-sample evidence, not
a stable held-out gain. Evolution and test share the core Codex actor and
Verus+Lynette scoring mechanism, while baseline skill, a two-word prompt
cleanup, context declaration, capability flags, and the val/test tasks differ.
The 262,144 test context was nonbinding for every audited prompt.

Measured report:

- `skillopt-verusage/refine-logs/FIXED_TEST20_RESULTS_20260820.md`

### Official Verus Targeted Rerun and Image Setting Audit (2026-08-20)

Comparison with `WechatIMG221.jpg` found that the old July Verus explains one
task of undercounting in every completed blank/S2 actor condition, but not the
full DeepSeek or GLM gap. Fresh actor reruns of the two version-sensitive
IronKV tasks under official commit
`ddc66116aa7a844a9e19cc50922fe85c84b8b4a5` were 1/2 in all six GPT,
DeepSeek, and GLM blank/S2 conditions: `f24cf9cc9db98c56f792` solved and
`826687f9c56eb8e65d5d` timed out at 600 seconds. All 12 results were valid.
Combining the unchanged other 18 outcomes with these fresh results gives
interim corrected blank/S2 estimates of GPT 19/18, DeepSeek 14/14, and GLM
13/13. These are targeted corrections, not full official-Verus reruns.

The rerun added USD 1.947193 metered spend: USD 0.310558 DeepSeek and USD
1.636636 GLM; GPT used local quota. GLM blank/S2 still accumulated 17/21
recovered HTTP 429s and 193/372 aggregate thread-seconds of backoff at two task
workers. Thus the stable 12/20 GLM results remain throughput-confounded. The
screenshot does not expose the exact test/skill/prompt/verifier hashes or
upstream sampling contract, and its `Native baseline` is not established to be
the accepted S2. Do not merge its GLM 16/20 or Qwen 5/4 rows into the controlled
table yet.

The evaluator gained a repeatable `--item-id` filter and the launcher exposes
it through `SKILLOPT_TEST_ITEM_IDS`; default frozen test-20 behavior is
unchanged. All 75 SkillOpt-VeruSAGE tests pass. Next action: obtain the image
run contract, add provider-wide GLM request pacing or use one task worker,
then rerun both complete GLM test-20 arms under official Verus. Qwen remains
pending until an owned service is available.

Canonical audit:

- `skillopt-verusage/refine-logs/IMAGE_RESULT_SETTING_AUDIT_20260820.md`

The screenshot author's follow-up clarifies that those runs used the July
Verus and compared no skill with a baseline/native skill. That second treatment
is not established to be accepted S2; the likely native seed is the 838-byte
`initial.md` (`96a55758...`), whereas our test used the 4,179-byte evolved S2
(`15496115...`). Therefore our official-Verus blank/S2 two-task correction
must not be applied to the screenshot's baseline-skill column. Its questions 9
and 19 still require a fresh rerun with the exact baseline hash.

The GLM misalignment is quantitatively dominated by provider waiting. Complete
stable worker-2 blank/S2 runs accumulated 235/241 recovered 429s and
2,865/2,322 aggregate thread-seconds of backoff, averaging 143/116 seconds per
task. Removing only this wait from mean wall time gives 217/180 seconds, close
to the screenshot's 225/207. Failed tasks averaged 260/208 seconds of backoff,
versus 66/55 for solved tasks. The next aligned GLM run must reach negligible
429 waiting through one worker or global request pacing before scores are
compared.


## SkillOpt And Skill Entropy Literature Review (2026-08-19)

SkillOpt (arXiv:2605.23904v2) and Skill Entropy
(arXiv:2608.05139v1) optimize different objects. SkillOpt keeps the target
model frozen and validation-gates bounded edits to one external skill
document. Skill-Entropy RL changes model weights and rewards an emitted
per-step skill-label plan for matching the gold task's scalar average
transition-difficulty rank.

The latter is useful to this project as a switching/routing hypothesis, not as
a drop-in reward. Its "entropy" is a reference-model accuracy ratio rather
than Shannon entropy, and its RL reward does not compare the predicted and gold
skill sequences position by position. Different sequences can receive the
same reward when their average entropy ranks match. The paper's larger
base-to-final gains also include SFT and GRPO; the clean increment over
answer-only GRPO is +9.6 and +7.9 points on Qwen3-4B and Qwen3-1.7B.

The local accepted/rejected SkillOpt audit is consistent with a transition
problem: narrow Verus knowledge can solve one case while unconditionally
injecting it causes retained successes to time out. The warranted next design
is therefore a short global core plus triggered cards with abstention and
directed transition diagnostics. Do not transplant the published entropy
formula, revise locked S2, or inspect held-out test items. First repair or
exclude the nine harness-invalid IR tasks and predeclare a repeated paired
development-only routing ablation.

Canonical review:
`research_memory/projects/verus_self_evolving/literature/20260819-200347-skillopt-and-skill-entropy-comparative-literature-review/ENTRY.md`.
No raw or sealed data was read or modified.

## SkillOpt S1/S2 Four-Model Held-Out Evaluation (2026-08-21)

The final reference-aligned blank/S1/S2 matrix is complete on the frozen
VeruSAGE test-20. This result supersedes the earlier worker-20 and diagnostic
tables above. GPT-5.6 Sol scored 18/17/17, DeepSeek V4 Pro 14/14/14, GLM-5.3
15/15/16, and Qwen3.8-27B BF16 3/5/6. Blank-to-S2 deltas are therefore -1, 0,
+1, and +3. All 240 retained main results were provider-valid with unchanged
inputs, and every counted solve passed independent Verus and Lynette checks.
The five historical Claude-failed tasks do not explain the positive deltas:
GPT solved 3/2/2, DeepSeek 1/1/1, GLM 1/1/1, and Qwen 0/0/0 across
blank/S1/S2.

Score summaries hide task exchange. Qwen S1-to-S2 has three gains and two
regressions; GLM blank-to-S1 and GPT S1-to-S2 each contain one gain and one
regression despite tied aggregate scores. Candidate diffs support recurring
contract-first, semantic-bridge, structural-induction, and explicit
quantifier-antecedent mechanisms, but several transitions are not uniquely
explained by the S1-to-S2 text delta and must retain a search-variance caveat.
There is only one retained rollout per condition.

Known metered main plus official-two API spend is USD 9.21704 for DeepSeek and
USD 26.12293 for GLM, USD 35.33997 total; transport/error calls without
provider usage make this a lower bound. GPT uses local quota. Qwen API cost is
zero. Its main matrix spans 10,995.54 seconds on a shared 4-GPU TP service,
equivalent to 12.22 service-window GPU-hours that cannot be exclusively
attributed to the experiment. Qwen used BF16, and the shared checkpoint
revision was unreadable from this account, so it is not an exact replication
of the author's FP8 Qwen arm. This also deviated from the preregistered
owned/sequential Qwen service plan; shared contention can affect progress
under a 600-second cutoff. All 264 retained actor manifests inherited a stale
`auxiliary_dev_fidelity_smoke` stage label even though arm-level contracts
correctly record held-out purpose. Historical raw manifests remain unchanged;
the generator is fixed for future formal evaluation.

Fresh official-Verus two-task scores for blank/S1/S2 are GPT 2/2,2/2,2/2;
DeepSeek 1/2,0/2,1/2; GLM 1/2,1/2,0/2; and Qwen 0/2,0/2,0/2. The targeted
hybrid remains explicitly separate from a full official-Verus test-20 rerun.
The GLM total covers 60 main task rollouts (USD 21.75512) plus six
official-Verus task rollouts (USD 4.36780), not one 20-task condition. Next
action: repeat the six Qwen transition tasks and the GLM
`AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods`/
`AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok`
pair with multiple seeds and owned, revision-locked services before
claiming stable cross-model transfer.

A two-round independent read-only audit returned PASS after cost/runtime scope,
Qwen protocol deviation, stale manifest stage, causal wording, and aggregator
fail-closed issues were corrected or disclosed. The reviewer independently
reconciled all 24 model/skill/version conditions and 264 retained results and reran 46/46 plus 80/80
tests. Historical raw manifests were not rewritten.

A focused July-Verus presentation and three-panel figure were added on
2026-08-21. Test positions 9
(`IR__marshal_ironsht_specific_v__impl2__lemma_serialize_injective`) and 19
(`IR__single_delivery_model_v__impl2__send_single_cmessage`) are UNSOLVED in
all 12 model/skill conditions apiece. They contribute zero while remaining in
the denominator; this is not a hard-coded false or an exclusion. The only
final no-skill-to-S2 regression is GPT-5.6 Sol on
`AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req`.
Its S2 trace expands all `Step` variants and omits two existing domain lemmas,
which is consistent with skill-conditioned search interference, while one
rollout per condition is insufficient to separate that possibility from
search variance or to establish a causal skill effect.
The new figure reads directly from the frozen `per_task.csv` and compares only
no-skill with S2. Runtime and cost average all 20 tasks; no solved-only series
is shown. Cost bars use actual retained per-task provider billing and
explicitly exclude archived retries. DeepSeek price periods differ across
conditions, so those raw dollar bars are spending records rather than a
skill-cost comparison.

Canonical artifacts:

- `skillopt-verusage/refine-logs/SKILLOPT_S1_S2_CROSS_MODEL_FINAL_REPORT_20260821.md`
- `skillopt-verusage/refine-logs/JULY_VERUS_RESULT_AND_REGRESSION_ANALYSIS_20260821.md`
- `research_memory/projects/verus_self_evolving/experiments/20260821-130358-skillopt-s1-s2-four-model-held-out-evaluation/ENTRY.md`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/aggregate-live/`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/figures/july_verus_cross_model_summary/`

## GPT/GLM Skill Trajectory Case Study (2026-08-21)

A focused audit of held-out task `0a8f681e5d0104455f3b` explains the observed
model-dependent skill effect using only visible trajectory evidence. GPT-5.6
Sol solves under blank/S1/S2 but takes 339.54/479.03/464.71 seconds. The skill
arms increase cumulative input tokens from 1.420M to 2.402M/2.449M, changed
candidate checkpoints from 8 to 14/13, and failed Verus calls from 8 to 14/13.
S2 also delays the first edit from 98 to 154 seconds after 34 rather than 10
pre-edit commands. The supported mechanism is redundant contract-first
inspection plus finer verifier-guided decomposition, not the few seconds spent
reading the skill file.

GLM-5.3 changes from a 602.49-second timeout with 25 failed Verus calls to S1
and S2 solves at 558.54 and 502.87 seconds with 12 and 13 failures. Blank's
final proof leaves two semantic jumps open: unmarshalled-Pod metadata equality
and Pod equality to DynamicObject `object_ref` equality. The skill-conditioned
proofs explicitly establish the missing `metadata -> object_ref -> map key ->
stored object` injectivity chain with named predicates and quantified
antecedents. Because S1 already solves, the main supported ingredient is the
shared contract/bridge/bounded-iteration core; the S2-only additions are not
separately identified. This is one rollout per condition with no visible hidden
reasoning, so it is mechanism evidence rather than a stable causal estimate.

Durable note:
`research_memory/projects/verus_self_evolving/notes/20260821-180041-gpt-glm-skill-trajectory-case-study/ENTRY.md`.
Next action: run task-disjoint, repeated-seed clause ablations and test adaptive
routing that preserves bridge guidance while capping redundant inspection for
already-capable actors. No raw run or frozen source was modified.

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

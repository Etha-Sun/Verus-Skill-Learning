# Research Plan: Verifier-Grounded Trace Analysis

Status: draft for method review; no experiment launched. Date: 2026-10-10 Pacific.

## Problem anchor

Improve a frozen DeepSeek V4 Pro agent's ability to extract useful, transferable experience from long VeruSAGE repair traces, with downstream budgeted Verus-plus-Lynette success and efficiency as the goals. Start with the existing train40 and validation20. Evaluate Verus-specific claims on VeruSAGE; a claim of general code-generation benefit requires a later code-generation benchmark.

## Objective contract and current evidence

Primary endpoint: paired budgeted dual-pass solved rate under unchanged task/specification, verifier/toolchain, actor model, reasoning setting, permissions, and 600-second evaluation budget. Secondary endpoints: total actor tokens/time/cost per attempted task, timeout rate, successful-pair resources as a separately labelled conditional diagnostic. Include the full failed/timeout budget and offline extraction costs; report deployment break-even rather than assuming free offline learning. No information-gain, card count, readability, extraction-judge score, or card-read count substitutes for live success.

Latest reviewed local evidence: augmentation 31/40 versus 32/40 on val20 with two repeats, task-clustered 95% interval [-5,+10] percentage points; 71/78 augmentation cards have evidence from only one source task. Latest Executive comparison: 14/20 versus 15/20, actor time +7.3%, estimated cost +5.0%; three persistent hard tasks remain 0/14 across related historical episodes. Positive bundled repair results also exist: 15/20 versus 16/20, time -21.8%, cost -25.0%, but these mix card/index/library-permission changes and do not isolate trace-analysis quality. These observations motivate investigation, not a claim that long-context failure is established.

The checked fixed-80 manifest contains train40 / val20 / test20, split hash a71e2a3838c2222312cc2487fc35b6a24cbc924e0a917d5e9120499f0ba2b49c. CSV calls val selection. The additional test pool requested by the user needs provenance, duplicate/family overlap, and prior-exposure audit; do not redefine the frozen fixture or call repeatedly used validation unseen. Training success 39/40 followed an 1800-second collection budget and infrastructure repairs; it is not the 600-second baseline.

## Critical framing

Long-context positional/reasoning failures are plausible, but neither human difficulty nor general long-context benchmarks demonstrates a trace-analysis bottleneck in DeepSeek V4 Pro. More traces can contain redundant searches, flawed actions, hindsight, and missing snapshots. Failed traces are not automatically uninformative, and success does not make every action good. Trace analysis, rule applicability, consolidation, and inference-time use are competing bottlenecks.

The framing 'existing methods simply concatenate all traces' is too broad: ExpeL, SkillOpt, Trace2Skill, PlugMem, SKILL-KD, and DeFA already offer experience abstraction, grouped/contrastive analysis, or evidence-aware organization. Especially close are DeFA (dependency-guided attribution with downstream skill evolution), SKILL-KD (behavioral contrasts with adaptive reruns), and the separate EDA Trace2Skill paper (dense verifier feedback). Segmenting and adding a critic is not a sufficient novelty claim.

## Selected provisional method

Stable id: trace-analysis-verifier-contrast-v1. Value label: incremental but valuable, with novelty unproven. One dominant mechanism: change the unit of trace analysis from narrative summaries to evidence-linked state/action/outcome contrasts, then test whether their distilled rules transfer beyond the source task before admitting broad applicability.

Representation: each evidence item contains source task id, raw event span, exact pre/post candidate hashes where recorded, code delta, verifier/tool result, dependency/helper context, proposed lesson, applicability premises, abstention condition, and a separate observed-versus-inferred field. Do not infer a complete historical state or hidden reasoning when absent. Verifier pass alone is insufficient if the task/specification was weakened.

Offline analysis extracts these items at recorded verifier boundaries, retaining relevant reads, prior failures, and helper changes. Compare with ordinary chunking to determine whether structure matters beyond shortening context. The distiller produces the same budgeted skill format as all other arms. Reuse the existing SkillOpt reflection/consolidation and skill-injection/evaluation plumbing; introduce neither a new retriever nor a trainable reward model. The initial global core, runtime access mechanism, and all deployment settings remain common across compared arms.

Local replay, where exact snapshots/toolchain exist, can verify an observed pre/post difference or a deletion check; it does not establish that the entire execution would have succeeded under a different decision. Label absence of replay explicitly. Replay evidence is a diagnostic layer until a separate compute-matched ablation justifies its contribution. The primary new route should not silently receive extra teacher calls or extra retries.

## Three validation blocks

1. Data and bottleneck diagnosis (train only). Inventory all train40 source traces and existing snapshots without collecting new rollouts. Predetermine eight train probe tasks using project, trace-length strata, outcome and snapshot coverage; choose no validation tasks based on known gains. Compare direct long-context analysis, ordinary chunk-and-merge, and verifier-boundary evidence analysis on identical source-task pools. Fix aggregate extraction tokens/call allowance and final skill token budget. Log model/context limits and any actual input truncation; direct analysis may use file access if that is its documented baseline. Shared small blinded evidence audit checks unsupported claims, missing decisive edits, helper omissions, and applicability errors. Human/LLM ratings are mechanism diagnostics only. Stop if the purported long-context disadvantage is not observed; allow the research question to change to consolidation/applicability rather than forcing the premise.

2. Train-held-out transfer falsification. Use five fixed source-task-family folds of the 40 training tasks (eight tasks/fold where feasible). Every extraction/consolidation round excludes its target fold completely, including original traces, augmented descendants, final training solutions and previously distilled cards. Cross-fit is needed because 38-source hindsight branches and repaired78 may contain target-task ancestry. The same candidate does not get to read a target trace and then count the target rerun as transfer. Compare no learned memory, existing native SkillOpt (with the same fold exclusions), ordinary hierarchical trace analysis, and the evidence-contrast route. Reuse identical raw task pools, frozen analysis budgets, common runtime interfaces, and skill size caps. Start with the eight probe targets (four arms, one repeat = 32 bounded actor episodes); this is a feasibility screen, not a generalization result. If the screen is informative, run the remaining fold targets under a predeclared limit; repeated diagnostic tweaking of probe results stays development.

3. Frozen external validation. Select at most one candidate using train-only evidence, freeze extraction recipe and artifacts, then run val20 with the frozen current incumbent and candidate, two fresh repeats each = 80 actor episodes. Repaired78 may be a historical production comparator here if all its ancestry is train-only, but must not substitute for the fold-pure controls in block 2. Existing val20 is repeatedly observed development validation, not an unbiased final test. Report paired per-task differences and task-clustered uncertainty; repetitions do not increase the count of independent tasks. Preserve both primary success and resource tradeoffs. An untouched test set is a separate final gate after manifest/exposure audit and method freeze. A general code-generation claim triggers a separate benchmark contract before claiming cross-domain benefit.

## Resource and decision contract

This turn authorizes planning and review, not a new paid DeepSeek campaign. Proposed next execution unit: zero-model-call data inventory and evaluator preflight. Subsequent first pilot is capped at eight train targets, four arms, one repeat (32 actor episodes, at most 600 seconds each, two workers), plus a separately metered extraction allowance. Maximum actor budget is 5.33 aggregate actor-hours (about 2.67 ideal two-worker hours, excluding overhead); specify an API dollar ceiling before dispatch. No paid full cross-fit or validation is automatically authorized by pilot approval. Preserve valid timeouts; retries may replace only proven infrastructure-invalid attempts and all physical attempts remain charged in accounting.

Promising pilot signals: zero safety/lineage violations; no solved loss versus fold-pure SkillOpt; at least one additional solved task or a predefined >=15% aggregate actor token reduction without solved loss; all costs disclosed. These are engineering go/no-go heuristics, not significance or noninferiority tests. Reject or simplify if ordinary chunk-and-merge matches the route, replay cannot be grounded, apparent gains depend on source-task leakage, or improvements vanish after counting analysis and failed episodes. Do not keep searching the same 20 validation tasks until a favorable outcome appears.

## Autoresearch workflow

Select locally available ARIS research-refine for problem anchoring, critical review and minimal experiment design. Actual framework use is Markdown workflow execution by the current agent; no ARIS MCP is registered in this session. An external ARIS checkout and Claude Code CLI are present; Claude auth status reports a configured OAuth login. Test one bounded tools-disabled reviewer call through the official local Claude-review bridge command builder. The reviewer receives only this compact proposal, not raw traces, datasets or repository secrets. A review score is not research evidence or user spending approval. Keep DeepSeek V4 Pro as the experimental actor.

## References

[1] Liu et al. Lost in the Middle: How Language Models Use Long Contexts. 2023. https://arxiv.org/abs/2307.03172
[2] Zhao et al. ExpeL: LLM Agents Are Experiential Learners. 2023/2024. https://arxiv.org/abs/2308.10144
[3] Ni et al. Trace2Skill: Distill Trajectory-Local Lessons into Transferable Agent Skills. 2026. https://arxiv.org/abs/2603.25158
[4] Ma et al. SkillOpt: Executive Strategy for Self-Evolving Agent Skills. 2026. https://arxiv.org/abs/2605.23904
[5] Yang et al. PlugMem: A Task-Agnostic Plugin Memory Module for LLM Agents. 2026. https://arxiv.org/abs/2603.03296
[6] SKILL-KD: Contrastive Skill Distillation for LLM Agents. 2026. https://arxiv.org/abs/2607.28048
[7] DeFA: Dependency-Guided Failure Attribution for LLM Agents. 2026. https://arxiv.org/abs/2610.01256
[8] Trace2Skill: Verifier-Guided Skill Evolution for Long-Context EDA Agents. 2026. https://arxiv.org/abs/2605.21810
[9] Yang et al. ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration. 2026. https://arxiv.org/abs/2605.03042
[10] ResearchClawBench: A Benchmark for End-to-End Autonomous Scientific Research. 2026. https://arxiv.org/abs/2606.07591

Local evidence: notes/20261010-133959-deepseek-augmentation-card-and-executive-results-synthesis-through-october-10/{ENTRY.md,TOKEN_TIMEOUT_STATISTICS.md,EVIDENCE.json}; fixed-claude-stratified-80-seed20260814/split_manifest.json; skillopt-verusage/src/skillopt_verusage/codex_reoptimize.py; scripts/analyze_train_proof_progress.py; skillopt-verusage/CHECKPOINT_CARDS.md.

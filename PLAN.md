# Plan

## 1. Map Link

- parent_map_node: hands-off trace distillation roadmap
- loop_id: m0-integrity
- node_objective: complete R036-R039 without opening sealed MA/NR trace content
- node_deliverable: reproducible corpus manifest, split/leakage audit, unified
  Copilot harness, and one non-claim mechanical smoke
- success_condition: all M0 provenance, leakage, usage, prompt, and safety
  checks are interpretable and durable
- abandonment_condition: sealed-data boundary cannot be enforced, or token and
  safety outputs cannot be reconstructed
- next_on_success: R040 select 20-50 train traces
- next_on_failure: repair the single failed M0 layer before any model scaling

## 2. Objective

- run id: handsoff-distill-m0-r036-r039
- experiment tier: auxiliary/dev, minimum evidence
- selected idea: Distill short verifier-grounded knowledge from successful
  frontier-agent trajectories, then test it with the same hands-off scaffold.
  M0 only establishes that data and evaluation are safe and measurable.
- user's core requirement: start the long-horizon plan now
- non-negotiable constraints:
  - raw claude_sonnet_gpt5 and all_batch_results-cyy-* remain read-only
  - do not inspect or distill MA/NR sealed trace content
  - do not treat R039 smoke as method evidence
  - preserve all existing dirty-worktree changes
- research question: Can the planned project split and Copilot evaluation path
  be implemented with auditable provenance, leakage checks, usage accounting,
  and verifier/checker outcomes?
- null hypothesis: M0 has an unresolved data or evaluator confound that blocks
  live token-efficiency claims.
- alternative hypothesis: M0 produces a frozen, reproducible integrity package
  sufficient to begin train-only distillation.

## 3. Current Node Tasks

- [x] recover selected idea, metric contract, and current workspace
- [x] R036 implement and generate corpus inventory
- [x] R037 freeze split and generate leakage audit
- [x] R038 implement/test unified Copilot harness
- [x] R039 execute one bounded non-sealed H0/H1/H2 smoke (local Qwen3.6 endpoint)
- [x] reclassify M0 after the resumed live smoke: GO for train-only M1 work
- [x] R040 select 30 de-duplicated successful train traces
- [ ] R041 distill and freeze <=800-token H1/H2 prompts

## 4. Baseline And Comparability

- baseline id: original Copilot hands-off task prompt
- baseline variant: H0, no injected knowledge
- dataset/split:
  - train directories: verified-anvil, verified-ironkv
  - dev directories: verified-atmo, verified-storage,
    verified-node-replication, verified-vest
  - sealed test directories: verified-memory-allocator, verified-nrkernel
- primary M0 metrics:
  - manifest coverage and duplicate-group counts
  - train-to-test exact/near-overlap counts
  - usage-accounting coverage
  - Verus and checker status availability
- required metric keys:
  - corpus_log_count
  - train_content_scanned
  - sealed_content_scanned
  - exact_train_test_overlap_count
  - near_train_test_overlap_count
  - harness_unit_tests_passed
  - smoke_usage_available
  - smoke_verus_checked
  - smoke_checker_checked
- comparability risks: corpus result variants, task-name normalization,
  Copilot auto-update/custom instructions, missing checker binary, and cache
  token parsing

## 5. Code Translation Plan

| Path | Current role | Planned change | Why | Risk |
|---|---|---|---|---|
| src/verus_self_evolve/handsoff_m0.py | new | metadata-only inventory and leakage audit CLI | R036/R037 | incorrect directory/project mapping |
| src/verus_self_evolve/handsoff_harness.py | new | isolated prompt runner and usage/safety parser | R038/R039 | Copilot/output format drift |
| tests/test_handsoff_m0.py | new | split, normalization, sealed-boundary tests | integrity | synthetic tests miss corpus variants |
| tests/test_handsoff_harness.py | new | prompt, usage, dry-run, safety parsing tests | comparability | external tools unavailable in unit tests |
| runs/handsoff_distill_20260719/m0/ | new | plans, manifests, logs, metrics, summary | durability | output collision |
| PLAN.md, CHECKLIST.md | stale control files | update for M0 | execution control | none |

No existing IG source, README, or modified CLI file will be changed.

## 6. Execution Design

- minimal experiment: R036-R038 plus unit tests
- smoke plan: copy one non-sealed IronKV source into three isolated
  workspaces; run H0/H1/H2 only after dry-run config equality passes
- full run plan: none in M0; main dev/test experiments remain blocked
- expected outputs:
  - m0/corpus_manifest.jsonl and corpus_summary.json
  - m0/split_manifest.json
  - m0/leakage_report.json
  - m0/metric_contract.json
  - m0/harness_manifest.json
  - m0/smoke/* run manifests, logs, usage, Verus/checker results
- stop condition: any sealed content read by inventory; unresolved exact
  train/test leakage; prompt conditions differ outside payload; usage or safety
  state absent from all smoke variants
- abandonment condition: no safe isolated workspace or no working live
  Copilot-compatible agent endpoint
- strongest alternative hypothesis: the existing corpus and Copilot logs are
  too heterogeneous for exact usage accounting, requiring a new live-only
  metric baseline

## 7. Runtime Strategy

- inventory command:
  PYTHONPATH=src python -m verus_self_evolve.handsoff_m0 inventory ...
- audit command:
  PYTHONPATH=src python -m verus_self_evolve.handsoff_m0 audit ...
- harness dry-run:
  PYTHONPATH=src python -m verus_self_evolve.handsoff_harness ... --dry-run
- smoke command: same harness without --dry-run, one condition at a time
- expected runtime: CPU work under 30 minutes; each agent smoke bounded to
  20 minutes, at most three variants
- logs: runs/handsoff_distill_20260719/m0/RUNLOG.md and smoke/*/copilot.log
- safe efficiency levers: metadata-only scans, content hashes only for train
  and evaluation inputs, one task, no retries without a concrete fix
- health signals: manifest row counts, zero sealed content reads, tests pass,
  Copilot process exits, usage line parsed, output file exists
- kill/relaunch: timeout, workspace escape, sealed path access, or config hash
  mismatch

## 8. Fallbacks And Recovery

- if Copilot endpoint fails: record external_dependency_blocked; do not replace
  it silently with another scaffold
- if checker binary is unavailable: Verus can validate smoke mechanics, but
  R038 remains PARTIAL until checker path is recovered
- if corpus mapping is ambiguous: freeze directory-level groups and mark
  project-code mapping unresolved rather than guessing
- if near-duplicate audit is too broad: retain exact hash/name audit and report
  near-duplicate coverage as partial

## 9. Checklist Link

- checklist path: CHECKLIST.md
- next unchecked item: R041 train-only prompt distillation and length control

## 10. Revision Log

| Time | What changed | Why | Impact |
|---|---|---|---|
| 2026-07-19 23:02 CDT | replaced stale offline-rule plan with M0 R036-R039 execution contract | user authorized start | old results remain untouched; new runs are auxiliary/dev |
| 2026-07-19 23:53 CDT | R036-R038 completed; six train traces quarantined after fixed-point leakage audit | initial directory split had IronKV/NR near-duplicates | effective train manifest now has zero exact/near sealed-eval overlap |
| 2026-07-19 23:53 CDT | R039 local mechanical fallback launched after frontier auth failure | GitHub Copilot OAuth/PAT absent | local QwQ result will not substitute for frontier method evidence |
| 2026-07-20 00:09 CDT | M0 classified PARTIAL | deterministic integration passes, but live model endpoint remains unavailable | do not start R040-R044 until R039 is completed |
| 2026-07-20 resumed | reopened R039 with local QwQ Copilot-compatible endpoint | user requested continuation | sufficient only for M0 mechanics; R042 frontier baseline still requires cloud auth |
| 2026-07-20 model recovery | QwQ direct and adapter runs produced no executable tool call; switch to previously tool-validated Qwen3.6-27B path | observable adapter trace isolated model/scaffold incompatibility | run forced tool-call endpoint test before another Copilot H0 |
| 2026-07-20 16:35 CDT | R039 mechanical smoke completed and M0 promoted to GO | H0/H1/H2 all have usage, candidate, Verus, and Lynette outcomes | begin R040; frontier R042 remains auth-blocked |
| 2026-07-20 16:42 CDT | R040 selected 30 unique verified train traces | balanced directory/model strata plus heuristic motif/error coverage | begin R041; no sealed trace content read |

# SkillOpt Next Model And Retrieval Configuration

## Metadata

- project: `verus_self_evolving`
- kind: `decisions`
- created_at: `2026-08-13T01:20:36-05:00`
- status: `complete`

## Decision Question

Which target/optimizer/memory/evaluation configuration is most likely to
produce an interpretable positive SkillOpt-on-VeruSAGE result, and what should
its budget be given the robust Flash ledger?

## Verdict

Action: `branch` from monolithic global-skill evolution to a small retrieval
pilot. Use GPT-5.6 Sol as the offline optimizer, DeepSeek-V4-Pro as the first
upgraded target after a bounded calibration, typed replay-supported cards as
the learned unit, top-1 proof-state retrieval with abstention, and a fresh
paired 20-task S0-versus-retrieval gate. Do not launch another unchanged
four-epoch global-skill run.

## Decisive Evidence

- Robust Flash epoch: S0 6/20, train 8/40, candidate 4/20; target cost
  USD 5.197054 for 80 task rollouts, with 35.528M prompt and 14.403M completion
  tokens.
- Flash candidate introduced no new solves, caused two paired regressions,
  grew from 838 to 10,322 bytes, and contained a false fold identity.
- Pro offline analysis was inexpensive but still made evidence-attribution
  errors; more optimizer output budget alone was not sufficient.
- GPT-5.6 Sol produced a compact audit-clean 3,490-byte candidate through the
  native eight-call optimizer workflow, but the Flash gate remained 4/20.
- Main SkillOpt has no proof-state runtime retrieval; it injects the whole
  current skill into every target call.

Evidence paths:

- `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER.md`
- `research_memory/projects/verus_self_evolving/notes/20260811-000000-skillopt-deepseek-v4-flash-epoch1-failure-analysis/ENTRY.md`
- `research_memory/projects/verus_self_evolving/notes/20260811-204930-skillopt-pro-reanalysis-and-retrieval-audit/ENTRY.md`
- `research_memory/projects/verus_self_evolving/experiments/20260812-000000-skillopt-gpt56sol-native-replay/ENTRY.md`

## Recommended Minimal Configuration

1. Reuse the stored 40 robust-v5 training trajectories; do not pay for another
   training rollout yet.
2. Use GPT-5.6 Sol/high offline to propose and criticize no more than 12 typed
   cards. Each card should be short, have positive and negative scope, cite
   verifier labels, and require replay for any concrete formula.
3. Retrieve at most one card at a valid Verus checkpoint using error/action
   family, project, type/mode, and structural anchors. Abstain below a frozen
   threshold and retain the 838-byte S0 unchanged.
4. Run an 8-task DeepSeek-V4-Pro calibration. Continue only with zero silent
   truncation and usable baseline capability. If Pro already solves more than
   15/20 on the frozen selection set, move to harder development tasks rather
   than trying to improve a saturated gate.
5. Run fresh S0 and retrieval conditions on the same 20 selection tasks
   (40 task rollouts). A minimal internal GO requires at least two fail-to-pass,
   zero pass-to-fail, zero Lynette regression, and no material cost increase.
   This remains a development gate, not population-level evidence.
6. Stop after one retrieval update unless that gate passes. Only then consider
   a second 40/20 step or any held-out test.

## Cost Basis And Estimates

Official rates per million tokens at decision time:

- DeepSeek-V4-Flash: USD 0.0028 cache hit, 0.14 cache miss, 0.28 output.
- DeepSeek-V4-Pro: USD 0.003625 cache hit, 0.435 cache miss, 0.87 output.
- GPT-5.6 Sol: USD 0.50 cached input, 5.00 uncached input, 30.00 output; requests
  above 272K input have a long-context uplift.

Repricing the exact robust Flash token ledger, without assuming that another
model changes trajectory length:

| Workload | Flash | Pro | GPT-5.6 Sol |
|---|---:|---:|---:|
| 20-task S0 profile | USD 0.97 | USD 2.99 | USD 92.04 mechanical reprice |
| 20-task Sol-candidate profile | USD 2.02 | USD 6.24 | USD 185.01 mechanical reprice |
| Full 80-task epoch profile | USD 5.20 | USD 16.01 | USD 484.77 mechanical reprice |

The GPT mechanical reprice is a stress bound, not the planning estimate. The
historical GPT-5.5 100-task Codex run was much more concise and projects to
USD 86-98 for 100 tasks at the same current Sol token rates, or roughly
USD 69-78 for 80 tasks and USD 34-39 for 40 task rollouts before long-context
uplift. That empirical prior uses a different harness and task mix.

Optimizer cost is secondary. The actual eight-call Sol optimizer used 246,313
input and 11,184 output tokens: local Codex metered dollars were zero; direct
API-equivalent Sol cost is USD 1.57, while repricing the same tokens as Pro is
about USD 0.12.

Planning ranges:

- Cheapest retrieval diagnosis, Flash target, 20 fresh S0 plus 20 candidate:
  about USD 3-4 target spend; Sol optimizer is zero metered dollars through the
  current local quota or about USD 1.57 API-equivalent.
- Recommended Pro retrieval pilot, including an 8-task calibration and paired
  20+20 gate: about USD 10-12 target spend under the Flash token-shape prior;
  add USD 0 with local Sol quota or about USD 1.57 for direct Sol API use.
- One full new 80-task epoch: about USD 5.2 with Flash or USD 16.0 with Pro,
  plus optimizer.
- Two 40/20 epochs with the initial baseline only once: about USD 9.4 target
  spend with Flash or USD 29.0 with Pro; direct Sol optimizer use adds about
  USD 3.1 across two epochs.
- GPT-5.6 Sol target: plan roughly USD 70-90 for one 80-task cycle from the
  historical GPT behavioral prior, not the USD 485 Flash-token stress bound.

Price sources:

- `https://api-docs.deepseek.com/quick_start/pricing/`
- `https://developers.openai.com/api/docs/models/gpt-5.6-sol`

## Why Alternatives Lose

- Flash target plus another global skill is cheapest but already failed with
  both weak and strong optimizers; repeating it does not address the learned
  representation or runtime routing problem.
- Pro optimizer plus Flash target changes only the cheaper component and does
  not fix Flash's execution ceiling.
- GPT-5.6 Sol as both target and optimizer maximizes capability but is too
  expensive for the first mechanism diagnosis and may leave little headroom
  on easier selection tasks.
- Four epochs are not justified before a single retrieval update passes a
  paired gate.

## Next Direction

Implement the retrieval-card shadow pipeline first. Before any live Pro calls,
freeze the card schema, replay support rule, retrieval threshold, abstention
behavior, 8-task calibration set, paired gate, and a new approval budget. The
prior USD 20 envelope has already been nearly consumed conservatively and must
not be silently reused as authorization for this new pilot.

## Data Safety

This decision used reviewed ledgers and compact summaries only. Raw and sealed
datasets were not modified, moved, or copied, and no model call was launched.


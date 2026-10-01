# Branch augmentation skill bank paper hypothesis and evaluation plan

## Metadata

- project: `verus_self_evolving`
- kind: `ideas`
- created_at: `2026-09-26T21:32:01`
- status: `draft`

## Objective

Assess whether checkpoint augmentation can support a paper on learning reusable
stage-triggered cards. The user proposes many existing trajectories, offline
augmentation, an extensible card bank, and a short main skill that lets the
agent retrieve relevant cards autonomously. This is a research proposal, not
authorization to launch a large new run or a verified method contribution.

## Context

Current evidence covers three training tasks and nineteen correlated checkpoints.
Matched original-only/augmented extraction produced four cards per condition.
Visible analysts compared branches; detailed evidence was omitted from merge
inputs. Utility validation remains stopped for trace-fidelity audit. Dynamic
retrieval is not implemented in that experiment; all four cards were injected
at startup. Existing test split remains sealed and unchanged.

## Method / Actions

Read compact local research memory and primary paper pages. The defensible
hypothesis to test is that deliberately generating alternative continuations
from a shared observable checkpoint yields more transferable, correctly scoped
decision guidance than retrospective summarization or equal-budget unguided
sampling. This is not an established novelty or causal claim.

Proposed architecture: offline aligned branch packets -> evidence-backed local
cards -> conservative deduplication and conflict/boundary retention -> searchable
bank. Online: fixed short main skill plus search/read tools; the agent chooses
when to search using the current goal, diagnostics, and previous action. Keep
retrieval simple and shared across conditions, but measure retrieval, reading,
application, and downstream outcomes. A diagnostic forced relevant-card exposure
can distinguish card utility from retrieval failures; it is not the main score.

Do not collapse the entire bank to four cards. Separate the bank capacity from
the per-query/context exposure budget. Card count alone is not evidence of
knowledge gain; corroboration should count distinct source tasks, not checkpoints.

Core comparisons: common main skill only; original-derived cards; equal-budget
no-hint resampling-derived cards; hinted branch-derived cards. All card banks
share format, extraction/retrieval configuration and exposure budgets. Add a
teacher-hint-only extraction control to distinguish verified branch evidence
from direct teacher distillation. Preserve ordinary SkillOpt as a practical
baseline without confounding its document format with the matched bank contrast.

Use task/family-separated train/development/test and held-out actor runs. Report
dual-validator success first, all-run tokens/costs/timeouts, and paired costs
on jointly solved items. Include teacher/extraction/indexing costs separately
and examine amortization. Expand unique source tasks before simply adding more
correlated branches. Align actor-visible state/history, model, tools and budget
for prospective branch comparisons; historical fresh branches lacking prefixes
cannot establish the effect of changing a decision inside an identical history.

## Evidence

Primary sources checked (focused scouting, not an exhaustive novelty review):

- [Voyager](https://arxiv.org/abs/2305.16291): growing executable skill library and retrieval.
- [ExpeL](https://arxiv.org/abs/2308.10144): experience-derived natural-language insights and recall.
- [Memp](https://arxiv.org/abs/2508.06433): trajectory-derived procedural memory, build/retrieve/update.
- [D2Skill](https://arxiv.org/abs/2603.28716): task/step skills, paired baseline/skill rollouts, utility and pruning in agentic RL.
- [BASM](https://arxiv.org/abs/2608.22339): explicit applicability, risk, avoidance and recovery fields. Boundary-aware cards alone are not a sufficient novelty claim.
- [CaSKG](https://arxiv.org/abs/2608.25500): textual counterfactual probes calibrate skill-graph relations for retrieval. Distinguish these probes from executed checkpoint continuation interventions; full comparison remains needed.
- [SkillOpt](https://arxiv.org/abs/2605.23904): local prior review at `literature/20260819-200347-skillopt-and-skill-entropy-comparative-literature-review/ENTRY.md`.

## Result

A paper direction is plausible but current three-task extraction is a mechanism
pilot, not sufficient empirical support. Experience-to-memory, step skills,
retrieval, and boundary fields already have close prior art. A stronger potential
contribution concerns how executed, verifier-grounded branch augmentation
acquires useful decision evidence and whether it improves unseen-task repair
at matched budgets. Formal verification supplies trustworthy outcome signals;
generalization and correctness of extracted causal explanations still need tests.

## Decision / Next Step

First repair fidelity checks and retain evidence through extraction/consolidation.
Then test a small matched original-card versus augmented-card retrieval pilot
before scaling augmentation. The no-hint resampling and teacher-only controls
are necessary for a stronger paper claim. No GPUs, new model inference,
trajectory reruns, raw-data modifications, or sealed evaluation reads occurred.

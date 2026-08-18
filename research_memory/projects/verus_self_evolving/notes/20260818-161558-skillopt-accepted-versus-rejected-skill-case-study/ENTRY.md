# SkillOpt accepted versus rejected skill case study

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-18T16:15:58`
- status: `draft`

## Objective

Audit the two accepted SkillOpt edits and the rejected main/slow candidates to
identify which guidance is general, motif-specific, or task-specific, and to
extract a defensible case-study takeaway without launching new experiments.

## Context

The canonical run is
`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/`.
It uses the same frozen 20-task selection IDs at S0 and E1--E4. Existing
lineage, per-task, skill, patch, slow-update, and repair artifacts were read in
place. No raw dataset or sealed test item was modified or read.

## Method / Actions

Compared S0/S1/S2 skill diffs, E2/E4 rejected main candidates, E2/E3/E4
rejected slow candidates, the E3 repair candidate, and task-aligned selection
status transitions. Read generated trajectory summaries for the two accepted
gains, rejected regressions, and the persistent infrastructure-blocked case.
Rules were classified as general operational guidance, reusable Verus proof
motifs, or task/family-specific recipes.

## Evidence

- Full Chinese case study:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/figures/fixed_selection_cost_performance/skill_case_study_zh.md`
- Minimal English report:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/figures/fixed_selection_cost_performance/skill_case_study_en.md`
- Exact accepted lineage and raw 100-row task table are beside those files in
  `skill_evolution_lineage_zh.md` and `fixed_selection_per_task.csv`.
- Main scores: S0 13/20, E1 accepted 14/20, E2 rejected 12/20, E3 accepted
  15/20, E4 rejected 14/20. Slow/repair candidates scored 12/20, 13/20,
  14/20, and 13/20 for E2 slow, E3 slow, E3 repair, and E4 slow.

## Result

Accepted S2 contains general workflow guidance and reusable Verus motifs but
no named AC, AL, or IR proof recipe. Rejected slow skills increasingly encode
narrow temporal/controller/infrastructure recipes. The strongest retrieval
motivation is E2 slow: it solved `aded79905be896942897` but made three retained
successes time out, for a net 12/20. Thus the optimizer can discover useful
narrow knowledge, while unconditional monolithic injection creates attention
cost and negative transfer.

All observed U-to-S and S-to-U transitions cross the 600-second timeout
boundary. Each condition has one stochastic rollout, the selection set is
reused, S2 lost 12/20 to S1's 14/20 in a fresh training comparison, and no
held-out test ran. The accepted edits are mechanism-consistent cases, not
stable causal solved-rate evidence.

## Decision / Next Step

Keep a short global core for contract-first reasoning, scope/safety, and
bounded iteration. Move quantifier, extensionality, temporal-existential,
controller-liveness, and IronKV-infrastructure knowledge into triggered cards
with abstention. Validate clause/card effects with matched multi-seed held-out
comparisons before claiming performance improvement.

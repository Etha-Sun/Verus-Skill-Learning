# SkillOpt on VeruSAGE feasibility proposal

## Metadata

- project: `verus_self_evolving`
- kind: `ideas`
- created_at: `2026-08-06T02:26:11`
- status: `complete`

## Objective

Determine whether Microsoft SkillOpt can be connected to the real VeruSAGE
repair scaffold through a leakage-safe, verifier-grounded feasibility pilot,
and freeze the smallest credible integration and evaluation contract.

## Context

- Canonical project state: `research_memory/CURRENT.md`
- VeruSAGE provenance audit:
  `research_memory/projects/verus_self_evolving/notes/20260703-093115-verusage-repair-scaffold-provenance-audit/ENTRY.md`
- R040 train-only selection:
  `research_memory/projects/verus_self_evolving/experiments/20260720-164228-r040-leakage-safe-stratified-train-trace-selection/ENTRY.md`
- Existing skill-evolution contracts:
  `skill-evolution-pilot/EXPERIMENT_PLAN.md` and
  `skill-evolution-pilot/INFORMATION_CONTRACT.md`
- Cloned upstream:
  `microsoft/SkillOpt@9639719632daecacd1baaa47fe781f3c0253600a`

## Method / Actions

- Read the SkillOpt research-engine adapter, split loader, trainer, gate,
  target-exec harness, configuration, and SkillOpt-Sleep boundaries.
- Read the VeruSAGE runner, main loop, orchestrator, central LLM interface,
  action base class, safety checks, and metadata path from the local
  read-only source checkout.
- Mapped the existing `skill-evolution-pilot` visibility, trace-fidelity,
  independent Verus/Lynette, and uncached-token contracts into the new design.
- Cloned SkillOpt into the isolated `skillopt-verusage/SkillOpt/` workstream
  and excluded the nested checkout from the parent repository.
- Wrote a versioned claim-driven experiment proposal and tracker. No
  dependencies were installed and no model or GPU experiment was launched.

## Evidence

- Proposal:
  `skillopt-verusage/refine-logs/EXPERIMENT_PLAN.md`
- Versioned proposal:
  `skillopt-verusage/refine-logs/EXPERIMENT_PLAN_20260806_022211.md`
- Tracker:
  `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER.md`
- Workstream guide:
  `skillopt-verusage/README.md`
- Upstream checkout is clean at
  `9639719632daecacd1baaa47fe781f3c0253600a`.
- Fixed-name and timestamped plan/tracker copies are byte-identical.
- The reviewed files contain no personal absolute paths or secret-shaped
  values.

## Result

SkillOpt is interface-compatible with VeruSAGE, but its default recipe is not
safe to run unchanged. The proposal freezes a thin adapter with:

- a central `SkillAwareLLMProxy` that appends the exact skill to all VeruSAGE
  target calls without modifying either upstream checkout;
- external-only per-rollout workspaces and V3-style trace fidelity;
- independent final Verus and Lynette validation;
- a 6/4/4 Anvil/IronKV effective-train split for train/selection/pilot;
- a scalar gate encoding in which one extra strict solve always dominates any
  token-cost difference, with batch-level safety veto;
- a minimal one-epoch, two-step patch-only SkillOpt loop with slow update,
  meta skill, and semantic-density rewards disabled;
- H0, fixed-seed, one-shot, and validation-best comparisons.

The conservative first-pass budget is about 34 VeruSAGE task rollouts and 272
nominal logical target calls under four repair attempts per rollout. Because
the native VeruSAGE client retries, the adapter must enforce a transport-level
cap of 12 actual provider requests per rollout, or 408 actual requests across
the first pass. These are planning limits, not executed costs or results.

No effectiveness evidence was produced. The design supports only an
Anvil/IronKV within-project task-held-out feasibility statement. It does not
support cross-project, sealed-test, R042, solved-rate, or token-efficiency
claims.

## Decision / Next Step

The main project next action remains R041 prompt distillation. If the SkillOpt
workstream is prioritized afterward, implement only the model-free
`SV-M0-UNIT` adapter/guard tests first. Do not launch target or optimizer model
calls until split, visibility, independent validation, token accounting, and
budget approval gates pass.

No raw or sealed data was modified, moved, copied, or committed. No sealed
content was read. Generated model outputs remain absent; future complete runs
must stay below `VERUS_SKILL_RUN_ROOT`.

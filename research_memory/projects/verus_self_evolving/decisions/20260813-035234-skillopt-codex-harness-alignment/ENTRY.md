# SkillOpt Codex Harness Alignment

## Metadata

- project: `verus_self_evolving`
- kind: `decisions`
- created_at: `2026-08-13T03:52:34-05:00`
- status: `complete`

## User Correction

Future SkillOpt experiments must use the Codex hands-off target harness aligned
with the SkillOpt rollout and evaluation contract. "Hands-off" alone is not a
sufficient specification. The intended harness is Codex CLI operating as the
task-solving agent, not the external `autoverus/verusage` Verus Copilot repair
scaffold with a DeepSeek proxy.

## Frozen Harness Decision

Use `skill-evolution-pilot/src/skill_evolution_pilot/codex_runner.py` as the
implementation reference for the SkillOpt target adapter. It provides a fresh
ephemeral Codex session per task, an isolated allowlisted workspace, immutable
`input.rs`, editable `candidate.rs`, optional exact `SKILL.md`, local Verus and
Lynette wrappers, normalized event capture, usage accounting, and independent
final validation.

For every SkillOpt comparison, keep the following target-side contract equal:

- Codex model and reasoning effort;
- base task prompt and tool permissions;
- task set, ordering/seed, timeout, and retry policy;
- Verus and Lynette binaries and final judge;
- fresh-session visibility and prohibition on old traces/reference proofs;
- usage, wall-time, and failure accounting.

Only the frozen skill condition may differ between S0 and a candidate or
retrieval arm. Selection, training rollout, post-update gate, and held-out
evaluation must all use this same Codex target harness. The GPT-5.6 Sol
optimizer is a separate SkillOpt component: it consumes the first rollout's
reviewed evidence, proposes an updated skill, and does not replace the target
harness contract.

The older `src/verus_self_evolve/codex_baseline.py` is useful evidence for the
Codex execution contract and cost prior, but new SkillOpt integration should
reuse the more explicit `skill-evolution-pilot` workspace/event protocol.

## Status Of The Active Pro Run

The already-started DeepSeek-V4-Pro paired run may finish under its approved
USD 12 cap so paid work is not discarded. It is a harness-mismatch diagnostic
and cost/capability control only. It must not be reported as the aligned
SkillOpt reproduction, even if its retrieval gate passes. No second epoch or
held-out claim may be launched from it.

Active artifact pointers:

- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-pro-calibration-8-v2-20260813`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-pro-retrieval-pilot-20260813/live_gate_v2`

## Next Action

After the active Pro tasks finish, close them out as a mismatched-harness
diagnostic. Before spending on another target batch, adapt the SkillOpt
`EnvAdapter` to the frozen Codex runner and run a small S0 smoke/A-A check.
Only then run the SkillOpt-aligned first rollout, GPT-5.6 Sol optimizer update,
and same-task Codex candidate gate.

## Data Safety

This decision read repository code and compact experiment ledgers only. It did
not modify, move, or copy raw or sealed data. Generated runs remain below
`VERUS_SKILL_RUN_ROOT`.

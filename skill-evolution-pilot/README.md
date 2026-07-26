# Skill Evolution Pilot

This directory contains the reviewed control documents for a three-objective
skill-evolution pilot. Large run artifacts must be written to:

```text
${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/<run_id>/
```

The three objectives are intentionally isolated:

1. reduce expected token cost to a verifier-safe solution;
2. improve the solve rate of an agentic Qwen3.6-27B solver;
3. improve pre/post terminal-repair-summary information gain.

The token objective is the first executable branch. The small-model branch
starts only after the OpenRouter adapter passes secret-redaction and trace
fidelity gates. The information-gain branch remains blocked until its full
proof target and scorer contract are frozen.

Control documents:

- `EXPERIMENT_PLAN.md`: hypotheses, stages, budgets, decisions, and stop rules;
- `INFORMATION_CONTRACT.md`: exactly what each agent may see and what must be
  logged;
- `DEBUG_GATES.md`: required smoke tests and launch gates;
- `TRACKER.md`: current status and the next executable action.

No API credential, raw trace, reference proof, or complete run directory may
be stored in this repository.

The executable module is `skill_evolution_pilot.cli` with
`PYTHONPATH=skill-evolution-pilot/src`. Its current commands cover:

- canonical Codex H0 and skill-conditioned runs;
- concurrent batch preparation/execution;
- lossless raw-event normalization and F3 audits;
- token-ledger reconstruction, aggregation, and H0 comparison;
- isolated token meta-agent generation and replayable visibility audits;
- four-task freezing with an explicit solved/unsolved screen label;
- env-only OpenRouter preflight.

All command outputs and generated workspaces are rejected unless they are
below `VERUS_SKILL_RUN_ROOT`.

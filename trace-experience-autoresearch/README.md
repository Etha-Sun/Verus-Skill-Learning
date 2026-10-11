# Trace Experience Autoresearch

Improve extraction of transferable experience from long VeruSAGE repair traces,
measured by downstream budgeted Verus-plus-Lynette success and efficiency.

The active research instructions are in [RESEARCH_BRIEF.md](RESEARCH_BRIEF.md).
Use it as the neutral opening brief for a fresh context. No existing repository
method, including the earlier evidence-record proposal, is the default research
direction. Independent opening hypotheses must precede exposure to those methods.

This directory contains the subproject's integration code and reviewed contracts.
Canonical research memory remains in `../research_memory/`. Datasets are read-only;
DeepScientist runtime state and full experiment outputs belong below an external
`VERUS_SKILL_RUN_ROOT`. Do not use the repository-local `runs/` setting: the current
data-layout validator rejects run roots inside the repository.

For convenient browsing, the ignored local `runtime/` symlink exposes the external
subproject output directory here. Its `deepscientist/` child contains service
state; `service-1.6.0.log` and `runtime_environment.json` sit alongside it. The symlink
does not relocate the running service or change the configured output root.
Future commands must use the external `VERUS_SKILL_RUN_ROOT` recorded in the
ignored machine-local context. On another machine, recreate the link to that
machine's selected external output directory.

## Model roles

- Research controller: Codex runner, explicitly pinned `gpt-6.1-sol`, reasoning
  effort `high`. This is an integration choice, not a comparative quality result.
- Evaluated repair agent: frozen `deepseek-v4-pro`, reasoning effort `max`, with
  the existing evaluator and accounting. No actor model change is implied.
- A learned trace analyzer's model is an experimental variable: freeze it across
  compared extraction methods before running the pilot. Controller choice does
  not determine the analyzer model.

## Execution

The independent opening is complete. `prepare_packet.py` creates an outcome-blind
training holdout and copies permitted donor traces. `evaluation_adapter.py`
reuses the existing isolated actor/evaluator with bounded provider accounting.
`run_campaign.py` launched the first frozen pilot. Active control has moved to
DeepScientist's native `autonomous` scheduler: it owns monitoring, analysis, the
next research decision, and evaluator invocation through `bash_exec`. The old
outer coordinator was retired without stopping its actor child. Do not restart
it or launch a duplicate analysis controller.

The current cycle has eight training probes and nineteen donor tasks after
module/name-family exclusions. Historical donors used an 1800-second collection
budget and an initial generic policy; the new actor comparisons all use 600
seconds. These exclusions do not establish a complete semantic clone/dependency
boundary, and the pilot is development evidence.

Two plumbing smoke episodes have completed with valid provider evidence. The
bounded pilot schedules four arms on eight tasks (32 attempts). A shared estimated
USD20 actor/analyzer ceiling is a coordinator-selected phase limit; controller
consumption is recorded separately. The ownership receipt is in
`runtime/native_ownership_handoff.json`. Live progress is in
`runtime/backend/batches/pilot-001/progress.json` and the native quest's monitoring
artifacts. `runtime/campaign_state.json` records the migration and is no longer
updated by the retired coordinator. The first pilot remains frozen and unchanged.

DeepScientist may continue choosing useful bounded studies totaling at most40 new
attempts within the same spend ceiling, using the training probes or20 exposed development
validation tasks. No validation answers, prior outcomes or test data are supplied.
The next study's method, controls, task membership and analysis are its own
scientific decisions, frozen before execution. Later contexts may use a different
declared allocation; the first pilot's1024-byte allocation stays fixed.

`watch_controller.py` provides a persistent lifecycle guardian in addition to the
native scheduler. It checks every60seconds and resumes a completed but stale
controller after a300second grace period, with a600second recovery cooldown. It
checks real controller processes, respects explicit stops and resource checkpoints,
and never invokes the evaluator itself. A known framework scanner error on raw JSON
arrays is repaired through the quest's projection repair script; raw artifacts stay
unchanged. Full guardian state and recovery logs live in the external runtime's
`lifecycle-guardian/`. Use `--home`, `--quest-id` and `--state-dir` with the machine's
external paths. Launch outside a process namespace sandbox so live processes are
visible; a file lock prevents duplicate guardians. This guard repairs stalled turn
handoffs; it does not restart a failed daemon or interrupt a hung live model call.

Historical planning records for the parent coordinator are under (do not include
them in the independent researcher's opening packet):

- `../research_memory/projects/verus_self_evolving/ideas/20261010-160133-trace-analysis-research-objective-and-autoresearch-plan/OBJECTIVE_CONTRACT.md`
- `../research_memory/projects/verus_self_evolving/ideas/20261010-160133-trace-analysis-research-objective-and-autoresearch-plan/FINAL_PROPOSAL.md`

The user authorized research to start, with 600-second task inference and optional
justified matched 900-second comparisons. Controller consumption is accounted
separately. The old USD15 four-arm pilot is historical planning, not the selected
experiment. The active frozen contract, when created, is referenced by the quest's
`PILOT_FROZEN.json`; do not replay an already dispatched campaign or retry ordinary
failures under new names.

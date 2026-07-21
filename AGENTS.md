# Repository Agent Instructions

This repository is the only active development workspace. The legacy
`verusys-result` tree is read-only data and historical-run storage.

## Startup Context

- If `.agent-context.local.md` exists, read it for machine-local paths. It is
  local-only context and must not be committed.
- For research tasks, read these files in order before acting:
  1. `research_memory/BOOTSTRAP.md`
  2. `research_memory/CURRENT.md`
  3. `research_memory/INDEX.md`
  4. `research_memory/projects/verus_self_evolving/PROJECT.md`
- `./research_memory` is the canonical research memory for this repository.
  This repository rule overrides any global skill or instruction that still
  points research-memory writes at the legacy `verusys-result` directory.

## Local Skills

- Optional project-local skills are installed below `.agents/skills/` from an
  external ARIS checkout. Both the links and their machine-local manifest are
  ignored and must not be committed.
- Do not edit symlinked skills in place. Update the external checkout and run
  its project installer with `--reconcile --no-doc`.

## Working Style

- Think before coding. State material assumptions, surface ambiguity, and ask
  before choosing among interpretations that would materially change scope.
- Prefer the simplest implementation that fully solves the requested problem.
  Do not add speculative features, abstractions, or configurability.
- Make surgical changes. Match the existing style, preserve unrelated work,
  and remove only unused code created by your own change.
- Work toward explicit, verifiable success criteria. For multi-step work, give
  a brief plan that pairs each step with its verification.

## Data And Output Safety

- Treat all raw datasets and sealed data below `VERUS_SKILL_DATA_ROOT` as
  read-only. Never modify, move, rename, or commit them.
- Write generated experiment outputs only below `VERUS_SKILL_RUN_ROOT`. Keep
  only reviewed compact summaries, contracts, and pointers in this repository.
- Do not commit personal absolute paths, secrets, API credentials, raw traces,
  sealed data, meeting transcripts, token tables, or complete run directories.
- All newly created files and directories must use English ASCII names.

## Research Evidence Boundaries

- Information gain is a secondary offline proxy, not the primary endpoint.
- R040 is complete, R041 prompt distillation is next, and the R042 frontier
  experiment is not complete.
- Do not claim that distilled knowledge improves solved rate or token
  efficiency until leakage-safe live evaluation directly establishes it.

## Research Closeout

Before finishing non-trivial research work:

1. Update `research_memory/CURRENT.md` with the active result, caveat, and next
   action.
2. Run `python3 research_memory/scripts/mem.py index`.
3. Report the durable memory/artifact paths and confirm raw-data safety.

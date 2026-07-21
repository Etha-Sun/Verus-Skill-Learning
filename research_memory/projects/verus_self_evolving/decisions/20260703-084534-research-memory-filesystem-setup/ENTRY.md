# research memory filesystem setup

## Decision

Use `research_memory/` as the canonical project memory filesystem for future
Verusage / self-evolving proof-repair work, and install a Codex skill named
`research-memory` so future agents are reminded to store research outputs,
plans, experiments, and decisions in this structure.

## Alternatives Considered

- Keep writing artifacts into ad hoc analysis directories. Rejected because
  future agents must rediscover context manually.
- Put everything inside `verus-self-evolve-scaffold/`. Rejected because memory
  should cover multiple repos, analyses, and meeting-derived notes.
- Copy raw data into a new memory area. Rejected because raw trace directories
  are large and should remain read-only.

## Evidence

- Memory root: `research_memory/`
- Project file: `research_memory/projects/verus_self_evolving/PROJECT.md`
- Helper CLI: `research_memory/scripts/mem.py`
- Codex skill: `<user-home>/.codex/skills/research-memory/SKILL.md`

## Risk

The main risk is that agents ignore the convention and keep creating scattered
analysis directories. Mitigation: use the `research-memory` skill and rebuild
`research_memory/INDEX.md` after creating entries.

## Next Action

Use this memory system for the next split-aware evaluation design and for all
future literature/experiment/decision entries.

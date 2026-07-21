# Bootstrap For Context Recovery

This is the first file a future agent should read when context is missing.

## Read Order

1. `research_memory/CURRENT.md`
2. `research_memory/INDEX.md`
3. `research_memory/projects/verus_self_evolving/PROJECT.md`
4. The latest relevant entry under `research_memory/projects/verus_self_evolving/`
5. If code or metrics are needed: `verus-self-evolve-scaffold/docs/eval_summary.md`

## Current Project

Default project id: `verus_self_evolving`

Main objective:

> Build a self-evolving Verus proof-repair scaffold that mines verifier-grounded
> skills, skeletons, and structured decision rules from traces, while preventing
> raw-data pollution and evaluation leakage.

## Non-Negotiable Data Rule

Raw data directories are read-only:

- `all_batch_results-cyy-claude/`
- `all_batch_results-cyy-claude-s4/`
- `all_batch_results-cyy-gpt5/`
- `all_batch_results-cyy-o4mini/`

Derived outputs belong in `research_memory/`, `verus-self-evolve-scaffold/`, or
a dedicated run directory.

## How To Save New Context

For formal artifacts:

```bash
python3 research_memory/scripts/mem.py new --project verus_self_evolving --kind <kind> --title "<title>"
python3 research_memory/scripts/mem.py index
```

For quick conversational ideas:

```bash
python3 research_memory/scripts/mem.py log --project verus_self_evolving --text "<short note>"
```

Use formal entries for decisions, experiments, meeting notes, and literature
scouting. Use inbox logs for raw or not-yet-triaged ideas.


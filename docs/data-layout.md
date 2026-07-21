# Local Data Sources

## Contract

This repository does not own or distribute datasets. Each collaborator points
the same code at one locally available source:

```bash
export VERUS_SKILL_DATA_ROOT=/absolute/path/to/your/data-source
export VERUS_SKILL_RUN_ROOT=/absolute/path/to/your/run-output
export VERUS_SKILL_DATA_LAYOUT=legacy
```

The selected data root is read-only during experiments. The run root contains
all generated artifacts, must already exist and be writable, and must not
overlap either the data root or this repository. A local `.env` may hold these
values; it is ignored by Git.

Tool paths are configured locally in the same way:

```bash
export COPILOT_BIN=/path/to/copilot
export VERUS_BIN=/path/to/verus
export LYNETTE_BIN=/path/to/lynette
```

## Supported Source Shapes

Use `legacy` when the selected root already has the existing unversioned
shape:

```text
<data-root>/
  all_batch_results-cyy-claude/
  all_batch_results-cyy-claude-s4/
  all_batch_results-cyy-gpt5/
  all_batch_results-cyy-o4mini/
  claude_sonnet_gpt5/
    verified-*/
```

Use `versioned` when a local provider exposes:

```text
<data-root>/
  verusage-batch-v1/
    all_batch_results-cyy-*/
  handsoff-v1/
    verified-*/
  eval/
```

These are path adapters, not migration requirements. Different collaborators
may select different roots or layouts as long as their data follows the same
trace contract.

## Resolution Rules

Commands resolve `verusage` and `handsoff` paths from the selected environment.
Explicit `--data-root` and `--corpus-root` arguments take precedence for a
single command. Output paths remain explicit or derive from
`VERUS_SKILL_RUN_ROOT` in repository scripts, and active writers reject output
paths outside that root.

Validate the current selection with:

```bash
PYTHONPATH=src python3 -m verus_self_evolve.data_layout
```

The validator checks data-directory presence, run-root existence and
writability, and data/run/repository separation. It never writes to the
selected source or reads sealed trace content.

## What Git Stores

The repository may store schemas, expected directory names, hashes, split
metadata, synthetic fixtures, and compact reviewed summaries. It must not
store raw prompts, complete trajectories, sealed answers, token-level score
tables, checkpoints, or machine-specific paths.

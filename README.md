# Verus Skill Learning

`verus-skill-learning` learns verifier-grounded repair skills and decision
policies from Verus trajectories. The repository contains reusable code,
tests, configuration contracts, and reviewed summaries. Datasets and generated
runs stay outside Git.

The Python import package remains `verus_self_evolve` so existing experiment
commands continue to work.

## Repository Layout

```text
src/verus_self_evolve/  library and command-line modules
tests/                  data-free unit tests
configs/                dataset contracts and experiment configuration
scripts/                reproducible entry points
docs/                   architecture, data, and experiment notes
results/                reviewed compact result summaries only
analysis_verusage_trace_ideas_20260624/  trace-analysis research artifacts
atlas-verusage-reproduction/             public-safe ATLAS adapter source
refine-logs/                              experiment plans, audits, and reports
research_memory/                          durable public research context
idea-stage/                               focused research contracts
fixed-claude-stratified-80-seed20260814/  reviewed frozen benchmark fixture
skillopt-verusage/                        shared evaluator and SkillOpt handoff
trace2skill-verusage/                     pinned Trace2Skill producer, baseline, and adapter
```

The workstream directories are kept side by side so trace analysis,
self-evolution, information gain, and external reproductions can progress
without forcing all research artifacts into the Python package. They are
public-safe snapshots: raw datasets, full run directories, caches, model/API
responses, meeting transcripts, large trace-derived artifacts, and personal
absolute paths are excluded.

The tracked `fixed-claude-stratified-80-seed20260814/` fixture is the narrow
exception to the external-data rule. It keeps the shared split and test-20
byte-for-byte stable across methods. Treat it as read-only; it is a recurring
benchmark, not a sealed effectiveness test, and no run output or provider
ledger belongs there.

## Select Your Local Data Source

Each user selects one data source on their own machine. The source is not
copied into this repository and does not need to be shared with other
collaborators.

```bash
cp .env.example .env
# Edit .env to point at your own data and run directories.
set -a
source .env
set +a
```

Two source layouts are supported:

- `legacy`: `VERUS_SKILL_DATA_ROOT` directly contains
  `all_batch_results-cyy-*` and optionally `claude_sonnet_gpt5/`.
- `versioned`: the root contains `verusage-batch-v1/` and `handsoff-v1/`.

Validate the selected source without modifying it:

```bash
PYTHONPATH=src python3 -m verus_self_evolve.data_layout
```

Commands use the selected source by default. An explicit `--data-root` or
`--corpus-root` still overrides it for a single run.

## Run

Offline rule mining and replay evaluation:

```bash
scripts/run_offline_eval.sh
```

Prepare an information-gain probe:

```bash
PYTHONPATH=src python3 -m verus_self_evolve.cli ig-probe-prepare \
  --out "${VERUS_SKILL_RUN_ROOT}/ig-probe-sanity" \
  --limit 5
```

Run the data-free test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Evaluate the frozen Trace2Skill baseline through the same model launch,
accounting, timeout, isolation, and scoring path used by SkillOpt:

```bash
SKILLOPT_CHECK_ONLY=1 \
  trace2skill-verusage/scripts/run_native_official_fixed_test20.sh gpt
```

See [the Trace2Skill baseline handoff](trace2skill-verusage/README.md) for the
four-provider commands and frozen artifact provenance.

## Data Safety

Data sources are treated as read-only. All generated manifests, logs, token
tables, plots, and checkpoints belong under `VERUS_SKILL_RUN_ROOT`, which must
not overlap `VERUS_SKILL_DATA_ROOT`. Local `.env` files and run directories are
ignored by Git.

See [local data sources](docs/data-layout.md),
[repository layout](docs/repository-layout.md), and
[architecture](docs/architecture.md) for details.

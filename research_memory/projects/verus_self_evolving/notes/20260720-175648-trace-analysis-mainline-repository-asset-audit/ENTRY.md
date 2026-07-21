# Trace analysis mainline repository asset audit

## Objective

Determine how the public `verus-skill-learning` repository should evolve after
the user clarified that trace analysis, rather than self-evolution itself, is
the project mainline.

## Context

- Published repository: `https://github.com/Etha-Sun/Verus-Skill-Learning`
- Early trace analysis: `analysis_verusage_trace_ideas_20260624/`
- Refactored scaffold: `verus-self-evolve-scaffold/`
- ATLAS adapter: `atlas-verusage-reproduction/`

Raw Verusage and hands-off datasets remained read-only during this audit.

## Method / Actions

Performed a read-only file, code, dependency, and size audit. Compared the
functions in the 793-line early `local_experiments.py` monolith with the
published package modules, then inspected the standalone ATLAS reproduction
and the legacy top-level result scripts.

## Evidence

- `analysis_verusage_trace_ideas_20260624/` is 1.1 MiB and contains 58 files:
  mostly reports/tables, with one 793-line executable analysis script.
- `local_experiments.py` implements result/trace parsing, repetition gates,
  cross-model skeleton coverage, retrieval sanity checks, prompt-cost audits,
  skeleton/reroute export, and dataset summaries.
- The public package already refactors trace parsing, models, motif extraction,
  rule mining, offline replay scoring, and reporting into tested modules under
  `src/verus_self_evolve/`.
- Missing first-class trace-analysis capabilities are cross-model coverage,
  retrieval evaluation, prompt/context cost analysis, and a general summary
  CLI.
- `atlas-verusage-reproduction/prepare_traces.py` already imports the public
  package's loader/models, so ATLAS is a downstream trace exporter/consumer.
  The adapter is reusable; its `runs/` prompts, responses, and generated
  taxonomies are not source-repository material.
- Top-level `analyze_result.py` and `analyze_cost.py` are legacy scripts;
  `analyze_result.py` contains another user's absolute paths and should not be
  copied as-is.
- The local scaffold directory is about 685 MiB because ignored run outputs
  remain physically present, although those runs are not tracked by Git.

## Result

Use one repository, not separate self-evolve and trace-analysis repositories.
The shared trace schema/parser is the stable core; skill mining, information
gain, hands-off distillation, and ATLAS are downstream consumers or evaluation
tracks. The repository name `verus-skill-learning` remains appropriate, but
the current package/module hierarchy and README overemphasize self-evolution.

Recommended target layers:

```text
trace_analysis/     schema, loading, summaries, loops, cross-model, cost
skill_learning/     motifs, skeletons, rule/skill mining
evaluation/         replay, information gain, hands-off live evaluation
adapters/           ATLAS and other external trace formats
```

Do not copy the 793-line monolith, legacy result scripts, generated ATLAS runs,
or all 58 research files wholesale. Port missing behavior into small tested
modules and retain only a concise trace-analysis report plus reviewed compact
tables.

## Decision / Next Step

This is a recommendation pending implementation approval. First land a
trace-analysis core migration with synthetic tests and CLI commands; then port
the ATLAS exporter; finally reorganize downstream self-evolve/IG/hands-off
modules without changing scientific behavior.

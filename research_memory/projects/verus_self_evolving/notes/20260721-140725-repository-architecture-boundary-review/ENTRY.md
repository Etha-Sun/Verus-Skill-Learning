# Repository architecture boundary review

## Objective

Review whether the published `verus-skill-learning` structure correctly
represents trace analysis, skill learning, and self-evolution, and determine
what belongs in `src/`.

## Context

The user clarified that trace analysis and self-evolution are parallel research
workstreams rather than a single linear project hierarchy. The current public
repository uses the Python package name `verus_self_evolve` and places trace
loading, rule mining, information-gain experiments, and hands-off harness code
in one flat namespace.

## Method / Actions

Performed a read-only review of all tracked files, module imports, README,
package metadata, prior trace-analysis prototypes, and ATLAS adapter imports.
No code, data, or Git history was changed.

## Evidence

Current module classes:

- stable substrate: `models.py`, `data.py`, `data_layout.py`;
- trace features/analysis: `motifs.py`, parts of `scoring.py` and `report.py`;
- skill-learning prototype: `mining.py` and `CandidateRule`;
- experiment-specific code: `ig_probe.py`, `ig_analysis.py`,
  `logprob_scorer.py`, `three_target_analysis.py`, and all `handsoff_*` modules;
- mixed orchestration: `cli.py` eagerly wires stable and experimental commands.

The repository has no first-class `Skill`, `SkillEvidence`, `SkillLibrary`, or
promotion/provenance contract. `CandidateRule` is an offline rule-mining
artifact, not a general skill representation. Root `PLAN.md` and
`CHECKLIST.md` describe one hands-off experiment rather than the repository as
a whole.

## Result

The current structure is acceptable as an executable research scaffold but is
not a sound long-term architecture for `verus-skill-learning`. The package name
overstates self-evolution, the flat namespace mixes library and experiment
code, and copying more trace-analysis scripts into it would deepen the problem.

Research workstreams may remain parallel, but software dependencies should be
one-way:

```text
trace substrate -> trace analysis
trace substrate -> skill learning
trace analysis  -> skill learning inputs/evidence
skill learning  -> evaluation
self-evolution  -> trace analysis + skill learning + evaluation
```

Recommended target:

```text
src/verus_skill_learning/
  traces/
  analysis/
  skills/
  evaluation/
  adapters/
experiments/
  self_evolution/
  information_gain/
  handsoff/
  atlas_taxonomy/
```

Only reusable, deterministic, tested code with explicit read-only inputs and
external outputs belongs in `src/`. Research plans, model-specific harnesses,
one-off scoring pipelines, generated results, and taxonomy runs belong under
`experiments/`, `docs/`, external run roots, or research memory.

## Decision / Next Step

The user prefers preserving the current top-level workstream layout. Defer the
canonical-package and experiment relocation refactor: it would touch the source
modules, tests, CLI, scripts, documentation, ATLAS imports, and active external
commands, creating unnecessary churn during ongoing research.

Near-term recommendation: keep the existing `src/verus_self_evolve` internals
unchanged and represent reviewed research workstreams such as `refine-logs/`,
`research_memory/`, trace-analysis artifacts, and ATLAS material as top-level
directories. Promote individual functions into `src/` only when they become
reusable and tested.

The repository-root choice is resolved in favor of the minimal variant: keep
the current code at the GitHub root and add reviewed workstream directories.
An exact mirror of the outer workspace would move every tracked path beneath a
top-level `verus-self-evolve-scaffold/` directory and is deferred.

All local research content may remain in place, but public Git inclusion still
requires a path/secret/privacy audit. Raw datasets, `result-*` trees, full run
directories, model/API responses, caches, and manifests containing personal
absolute paths remain outside the public repository. Do not rewrite the
already published Git history.

## Implementation (2026-07-21)

Added four public-safe top-level snapshots to public `main` without changing
`src/verus_self_evolve`:

- `analysis_verusage_trace_ideas_20260624/`;
- `atlas-verusage-reproduction/`;
- `refine-logs/` and `idea-stage/`;
- `research_memory/`.

The audit found no retained personal absolute paths or symlinks. Raw datasets,
ATLAS runs, meeting transcripts, the 1.5 MB skeleton cache, and other local run
artifacts remain excluded. Existing uncommitted edits to root `PLAN.md` and
`CHECKLIST.md` were not staged.

The work was split across commits `eb4b9bc`, `56193d0`, `fdcf3da`, and
`37581a0`. No temporary review branch was retained locally or on GitHub.

# Matched no-hint continuations: 2026-09-19

The train-only matched no-hint arm is complete for the three source tasks. Each
continuation starts from the exact reviewed checkpoint source, uses the initial
skill, DeepSeek V4 Pro with high reasoning, and a 600 second actor limit. The
fresh actor sees neither the teacher hint nor the historical trajectory prefix.
Every checkpoint source was verified against the published selection SHA before
the run.

| Project | Checkpoints | Dual validated | Unique final sources | Exact match to either v1/v2 final |
|---|---:|---:|---:|---:|
| IR | 6 | 6 | 4 | 2 |
| AC | 6 | 6 | 6 | 1 |
| AL | 7 | 7 | 7 | 2 |
| Total | 19 | 19 | 17 | 5 |

All 19 results are provider-valid `V2_TRACE` records. Every result completed
within budget, passed the input and skill safety checks, and passed independent
Verus and Lynette validation. The provider ledger contains no error or
unmetered request. Estimated API spend for this arm is USD 2.246749.

The compact historical reports record 18/19 dual passes for hint v1 and 18/19
for hint v2, compared with 19/19 here. This is one rollout per condition and is
not evidence that hints reduce solved rate. The no-hint arm used Codex CLI
0.153.0 rather than the historical 0.146.1 and a newly built Lynette binary;
only the Verus release is an exact historical match. The no-hint arm also used
more actor output in aggregate than either hint arm. Runtime drift and search
variance prevent a clean causal efficiency comparison.

Endpoint identity is limited evidence about reasoning identity. Five no-hint
final sources exactly equal a v1 or v2 final source. The other fourteen are
source-distinct, but may still implement the same mathematical strategy. For
example, AC CP6 independently ran Verus, identified the two unsupported
`#![auto]` attributes, removed only those lines, and passed both checks without
seeing the teacher diagnosis.

Complete no-hint traces, raw Codex events, snapshots, condition contracts,
provider ledgers, and final candidates are external under
`${VERUS_SKILL_RUN_ROOT}/skillopt-fork-no-hint-20260919/`. The reviewed aggregate
is `summary.json` in that directory. Raw benchmark sources and the compact
publication were not modified.

The next SkillOpt step remains blocked on the absent complete historical
original, v1, and v2 run directories. The compact publication is sufficient to
freeze checkpoint sources and compare audited endpoints, but it must not be
expanded into fabricated complete trajectories. Once those run directories are
mounted, export the three task-grouped fork packets and run the hint-visible
diagnostic described in [README.md](README.md).

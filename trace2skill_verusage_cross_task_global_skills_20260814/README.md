# Cross-task global skill experiments

This directory is the workspace for learning global Verus proof-repair skills
from the fixed AC/AL/IR split and evaluating them with Codex CLI + DeepSeek V4
Pro.

The experiment intentionally keeps three Trace2Skill construction methods:

- `semantic-v4`: model-induced semantic families, provenance-preserving global
  reconciliation, and a compact `(M, R)` layout;
- `compressed-skill`: the native Trace2Skill-style MAP/REDUCE compression and
  patch application path;
- `semantic-reduce`: the same native MAP and patch application path, with MAP
  items routed into model-induced mechanism families and native REDUCE applied
  only within each family.

For each construction method, the plan preserves a direct Trace2Skill version
and adds an optional SkillOpt-inspired held-out-gated version. The no-skill arm
is the common actor baseline.

The gate is controlled by one configuration value:

```json
{"held_out_gate": {"enabled": false, "expected_task_count": 20}}
```

With `enabled=false`, candidate snapshots are promoted directly and no
validation actor is called. With `enabled=true`, the same complete snapshots
are compared lexicographically: success cannot regress; success gains must
stay at or below the local and frozen-M-core `1.20 x` provider-total-token
ceilings; equal-success candidates must stay at or below `1.10 x` and establish a material
`15%` token or `10%` wall-time gain with at least `5%` combined efficiency.
Primary uncached tokens measure economic efficiency, provider total tokens
enforce hard bloat caps, and reasoning tokens remain a separately reported
auxiliary component. No-skill is a reporting/final-evaluation control and is
never the iterative incumbent. The controller is shared, but the candidate
unit remains method-specific: native compressed patch bundle or
semantic-reduce family bundle.

## Frozen data

- Dataset: `../fixed-claude-stratified-80-seed20260814/`
- Source branch: `feature/skillopt-verusage-20260812`
- Source commit: `d33b1ecbe4042c5ae282e15715366fbaa41b2186`
- Split: 40 train / 20 val / 20 test
- Projects: Anvil C (`AC`), Anvil L (`AL`), and IronKV (`IR`)

The dataset directory is an unmodified extraction of the teammate-provided
commit. This experiment does not redefine or replace its distribution.

## Local configuration

The fixed split is local-only and is not committed. Generated construction,
translation, actor, and validation outputs must remain below
`VERUS_SKILL_RUN_ROOT`. The actor runner accepts explicit CLI paths and also
uses these optional environment variables for portable defaults:

- `VERUS_SKILL_SCRATCH_ROOT`
- `VERUS_SKILL_RUN_ROOT`
- `VERUS_RUST_ROOT`
- `DEEPSEEK_ENV_FILE`
- `CODEX_BIN`
- `VERUS_BIN`
- `LYNETTE_BIN`

## Current state

The offline implementation now includes:

- native `--reduce-strategy global` behavior unchanged by default;
- `--reduce-strategy semantic` for semantic routing followed by within-family
  native REDUCE and deterministic cross-family coalescing;
- the aggregate-only held-out controller and `held_out_gate.enabled` switch;
- a host-private snapshot-score cache and append-safe gate-history resume;
- one shared frozen markdown MAP producer for both REDUCE arms;
- method-specific construction runners plus a versioned candidate schedule and
  immutable parent/M-core lineage contract;
- a shared sequential TRANSLATE/APPLY materializer for native bundles and
  semantic-family bundles;
- fake-evaluator/unit tests for direct merge, lexicographic promotion,
  cumulative M-core caps, hard audit vetoes, paired transition accounting,
  exact semantic partitioning, and one-reference-per-family translation units.

The shared 40-record memory extraction and semantic-v4 M-core construction are
complete. The frozen root-only M-core has 90 lines, zero references, and tree
hash `85d3bfb5c7bed2c3b1b9f8ea7cb83129873207270ae9509e4c0d1be3473e21eb`;
its compact snapshot is committed under
`frozen_m_core/verus-proof-repair/`. The shared MAP produced 19 stable items. Native global REDUCE produced one
Candidate; semantic routing produced 12 mechanism-family Candidates and used
native REDUCE only within each family.

The fixed 20-task validation run completed: no-skill solved 16, `M_core`
solved 14, the native Candidate solved 13 and was rejected, and the final
semantic incumbent solved 17. Semantic Candidates 1 and 4 were accepted;
Candidates 8 and 11 also solved 17 but failed the resource/efficiency gate.
The final Candidate-4 tree hash is
`88fd2f6c456d01738c23c667a377a6bd92a3e85b6ffbda5254b86302503cbeef`;
the compact frozen snapshot is committed under
`final_skill/verus-proof-repair/`.
Its 20-task run averaged USD 0.04112 and 313.65 wall-time seconds per task; the
17 successful tasks averaged 207.22 seconds. These are validation-selection
results only. The sealed test remains unread and unexecuted.

Run the offline tests from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s trace2skill_verusage_cross_task_global_skills_20260814/tests -v
```

See `meet0818.md` for the final validation matrix, Candidate-family
interpretation, and compact result summary.

# Trace2Skill producer and baseline integration

This directory makes the Verus Trace2Skill method reproducible and publishes
the frozen baseline used by the repository's shared fixed-test evaluator.
Trace2Skill and SkillOpt retain different skill-construction pipelines; model
launch, token accounting, timeouts, isolation, and scoring are owned by the
common evaluator under `skillopt-verusage/`.

## Producer

The production runtime is self-contained under `vendor/trace2skill_verus/`.
Its prompt-driven `skill_evolver/` runtime is migrated from the repository
snapshot at commit
`92a1e8ab55d79b0831f251bbd9b9e61e1562bc9e`, path
`trace2skill_verusage_baseline_test/code/`. The four frozen Verus prompts and
neutral Verus seed are part of the integration, so execution does not clone or
download Trace2Skill source code at runtime. The verified runtime tree is
`e8ef9e77436b0641f0e65b3bc216f202e05235021103a2b7a956009638f88adf`.
The runtime keeps only the thin model client needed to execute skill-generation
prompts. The deprecated ReAct task-solving harness is excluded; produced skills
are consumed and evaluated through the shared Codex CLI harness.

Only the native global MAP/REDUCE construction path is exposed. The custom
semantic REDUCE/router, semantic-v4, M_core, candidate-gate, and legacy
evaluation-bridge paths from the experiment bundle are deliberately excluded.
The historical frozen artifact was originally constructed from official
Trace2Skill commit `3d0b52a140f002a512930252b613c49048f7d5ac` with the Verus prompt
adaptation; `PROVENANCE.json` records that historical fact separately from the
integrated Verus runtime source.

Install the checked-in runtime dependencies:

```bash
python3 -m pip install -e '.[test,trace2skill]'
```

The producer consumes normalized Trace2Skill analysis records derived from
training trajectories. Raw trajectories and generated model responses remain
outside Git. For the published native official baseline, the wrapper requires
the exact 40-record input hash recorded in `PROVENANCE.json`.

Run the zero-network producer preflight:

```bash
trace2skill-verusage/scripts/run_native_official_producer.sh \
  --check-only /absolute/path/to/combined_records.json
```

After reviewing the preflight, execute the construction under the external run
root:

```bash
trace2skill-verusage/scripts/run_native_official_producer.sh \
  --execute /absolute/path/to/combined_records.json
```

The execution uses the historical native global configuration: combined
failure/success records, batch size 1, merge batch size 5, four MAP workers,
five merge levels, JSON patches, translation enabled, and up to three
verification-fix rounds. Credentials are read from the named environment
variable and are never placed in the command or manifest.

## Frozen baseline

- label: `native-official-20260819`
- entry point: `baselines/native-official-20260819/skill/verus-proof-repair/SKILL.md`
- bundle file count: 10
- entry-point SHA-256:
  `40de0d04f2f4e2b05a0d8187439251f2e381b2f4675c2ef44247519acf9452bd`
- shared `skill-tree-v1` SHA-256:
  `195ab1294871689873e3bd6d9d2dbfb0a89a0d13b2ea0bdd1f7d716d826437c2`

The artifact and four construction prompts are copied byte-for-byte from
commit `92a1e8ab55d79b0831f251bbd9b9e61e1562bc9e`.  The accompanying provenance is
sanitized: it records reproducibility facts and hashes but contains no local
paths, credentials, raw trajectories, evaluation results, or token tables.

The older experiment documentation reported a different legacy tree hash for
the same files.  New unified evaluations use the repository's
`skill-tree-v1` contract and the hash above.

## Evaluate

From the repository root:

```bash
trace2skill-verusage/scripts/run_native_official_fixed_test20.sh gpt
trace2skill-verusage/scripts/run_native_official_fixed_test20.sh deepseek
trace2skill-verusage/scripts/run_native_official_fixed_test20.sh glm
trace2skill-verusage/scripts/run_native_official_fixed_test20.sh qwen
```

The launcher delegates to
`skillopt-verusage/scripts/run_s2_fixed_test20.sh`; it does not implement a
separate bridge or scoring path.  Before spending model quota, validate one or
all providers with:

```bash
SKILLOPT_CHECK_ONLY=1 \
  trace2skill-verusage/scripts/run_native_official_fixed_test20.sh gpt
```

For a pre-merge smoke test, restrict the shared evaluator with
`SKILLOPT_TEST_ITEM_IDS=<item-id>`.  A formal four-provider rerun should begin
only after this integration is merged to `main`, so the result provenance
points at the canonical commit.

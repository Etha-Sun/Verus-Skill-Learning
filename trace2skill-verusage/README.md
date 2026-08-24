# Trace2Skill baseline integration

This directory publishes the frozen Trace2Skill baseline artifact that is used by
the repository's shared fixed-test evaluator.  Trace2Skill and SkillOpt differ in
how they construct a skill; model launch, token accounting, timeouts, isolation,
and scoring are owned by the common evaluator under `skillopt-verusage/`.

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

## Run

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

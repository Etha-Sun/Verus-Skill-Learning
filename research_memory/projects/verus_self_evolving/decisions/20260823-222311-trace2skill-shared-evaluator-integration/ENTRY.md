# Trace2Skill shared evaluator integration

## Decision

Integrate the Trace2Skill method and frozen native official baseline from
feature state `92a1e8a` through a clean branch created from `origin/main`.
Mirror the SkillOpt dependency pattern: bootstrap the official Trace2Skill
producer at pinned commit `3d0b52a`, apply a reviewed Verus compatibility
patch and prompt overlay, and verify the patched Git tree. Publish the neutral
seed, final ten-file skill bundle, sanitized provenance, producer adapter, and
a thin evaluation launcher. The evaluation launcher delegates to
`skillopt-verusage/scripts/run_s2_fixed_test20.sh`, so Trace2Skill and
SkillOpt share model invocation, timeout, token accounting, isolation, and
scoring while retaining different skill-construction logic.

## Alternatives Considered

- Cherry-pick `92a1e8a`: rejected because it includes old bridges, runners,
  full historical results, and local experiment artifacts already superseded
  by main.
- Develop in the existing Trace2Skill worktree: rejected because that
  worktree contains unrelated tracked and untracked research changes.
- Copy a Trace2Skill-specific bridge: rejected because it would recreate the
  evaluation divergence this integration is intended to remove.
- Publish only the final artifact: rejected because main is also the method
  repository and should support reproducible construction, as it does for
  SkillOpt.

## Evidence

- Frozen entry-point SHA-256:
  `40de0d04f2f4e2b05a0d8187439251f2e381b2f4675c2ef44247519acf9452bd`.
- Shared `skill-tree-v1` SHA-256:
  `195ab1294871689873e3bd6d9d2dbfb0a89a0d13b2ea0bdd1f7d716d826437c2`;
  10 files and 39,562 bytes.
- Main readiness: 253 passed, 1 optional-Torch skip.
- GPT check-only validated the fixed test and split hashes, the artifact
  inventory, and formal Verus `release/0.2025.09.12.bb1f342`.
- One-item pre-merge GPT smoke on `59a26eebc3ccdb67c916`: 1/1 solved,
  zero timeouts, one V2 trace, and independent final Verus validation passed.
  Shared accounting recorded 217,049 input, 167,424 cached input, 3,450 output,
  and 1,418 reasoning tokens. The ignored diagnostic run is
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/premerge-trace2skill-gpt-smoke-20260823/`.
- Producer upstream is pinned at `3d0b52a`; the reviewed Verus runtime tree is
  `2acce50aada3759a9a853ebaab68579627e02978`. The neutral seed tree is
  `f67322cd47bc25f993f92788767b58047c11a6863d0d7a6ba987f5dff163d7a2`.

## Risk

The smoke covers the direct GPT path only. It does not establish four-provider
score, latency, or token parity, and direct GPT remains non-isolated. The
tracked test-20 is a recurring diagnostic benchmark rather than a sealed test.
No formal four-provider rerun has been started.

## Next Action

Review and merge the integration PR into `main`. Only after main contains the
frozen artifact and adapter should a separately approved formal four-provider
rerun begin, so run provenance points at the canonical commit.

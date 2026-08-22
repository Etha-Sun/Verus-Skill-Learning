# Vskill-0822 Trace2Skill Alignment Plan

## Scope

Selectively integrate the reusable parts of the upstream Trace2Skill experiment at
commit `92a1e8ab55d79b0831f251bbd9b9e61e1562bc9e` into the existing VeruSAGE
evaluation stack. This pass is model-free: it must not launch paid inference or
modify frozen datasets and historical runs.

The upstream legacy construction, memory-generation, and shared-train drivers are
out of scope because they depend on a second Skill Evolver tree and materialize
legacy trajectories. The existing local selection gate remains authoritative.

## Baseline And Contracts

- Branch: `Vskill-0822`
- Local baseline: `8a8b5878f2b8753f0e30f7657e1513f5ebba16b3`
- Frozen test-20 items SHA-256:
  `81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42`
- Formal verifier release: `release/0.2025.09.12.bb1f342`
  (`bb1f342683fd26de011825725a55325b65e7d359`)
- A result is solved when the final candidate passes Verus, Lynette, and input
  safety. Timeout and fidelity are separate measurements.
- `within_budget` is false for a timeout even when the final candidate is solved.
- V0/V1/V2 describes trace completeness only; V0 does not by itself invalidate a
  proof result or trigger a paid rerun.
- Cached input remains part of total input-token consumption. The figure shows
  cached and uncached input as a stack, output separately, and reasoning output as
  an output subset rather than an additive token category.

## Code-Change Map

1. Add immutable Trace2Skill candidate/snapshot lineage contracts and connect
   them to the existing held-out gate without duplicating its promotion policy.
2. Add the upstream actor mount/network isolation mechanism behind an explicit
   runner option, including a machine-readable isolation provenance manifest.
3. Centralize outcome classification and update test-20 summaries so correctness,
   timeout budget, safety, and fidelity cannot be conflated.
4. Enable the existing targeted GLM HTTP-429 retry/backoff in both actor contract
   profiles; keep all other retry behavior unchanged.
5. Add a verifier release contract/preflight and a data-driven two-panel token
   figure exporter/generator.
6. Add focused unit tests plus model-free smoke checks.

## Verification Tiers

### Minimum evidence

- Candidate lineage rejects mutation and provenance mismatches.
- Outcome tests cover solved timeout, unsafe timeout, V0 solved, and budget flags.
- Shell contract test confirms GLM 429 flags in both profiles.
- Verifier identity test accepts only the pinned release/commit contract.
- Figure data tests check `input = cached + uncached`, `reasoning <= output`, and
  `n = 20` for every plotted condition.

### Solid evidence

- Run the relevant `skill-evolution-pilot` and `skillopt-verusage` test suites.
- Run actor-isolation preflight/smoke when the host supports user namespaces;
  otherwise record an explicit unsupported result rather than silently weakening
  isolation.
- Generate PDF and PNG token figures from the reviewed aggregate matrix under
  `VERUS_SKILL_RUN_ROOT`, then render and inspect the PDF.
- Run a verifier-only identity check against the September 12 binary. A full
  test-20 rerun remains a separate, explicitly approved experiment.

## Stop Conditions

- Do not fall back from formal isolation without recording the fallback in the
  run manifest.
- Do not accept a verifier whose reported identity does not match the pin.
- Do not write into frozen split/data directories or existing run directories.
- Do not claim token/performance parity until a leakage-safe live rerun establishes
  it under the aligned contracts.

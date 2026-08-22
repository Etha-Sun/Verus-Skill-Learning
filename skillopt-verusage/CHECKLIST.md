# Vskill-0822 Trace2Skill Alignment Checklist

## Planning And Safety

- [x] Record branch, upstream commit, test-20 hash, and verifier pin.
- [x] Define correctness, timeout-budget, fidelity, and token accounting contracts.
- [x] Exclude legacy raw-trajectory construction and paid inference from this pass.

## Implementation

- [x] Add immutable Trace2Skill candidate/snapshot lineage.
- [x] Integrate actor isolation and isolation provenance with the Codex runner.
- [x] Separate proof correctness from fidelity and timeout budget accounting.
- [x] Enable targeted GLM 429 retry/backoff in both profiles.
- [x] Add the September 12 Verus release contract/preflight.
- [x] Add reviewed input/output token figure data and plotting scripts.

## Verification

- [x] Run focused unit tests for every changed contract.
- [x] Run the existing relevant regression suite (146 passed).
- [x] Run and record model-free actor-isolation smoke/preflight.
- [x] Verify the pinned Verus binary identity.
- [x] Generate vector/raster token figures below `VERUS_SKILL_RUN_ROOT`.
- [x] Render and visually inspect the PDF.

## Closeout

- [x] Review the final diff for unrelated changes and absolute paths.
- [x] Update `research_memory/CURRENT.md` with results, caveats, and next action.
- [x] Run `python3 research_memory/scripts/mem.py index`.
- [x] Commit the integration in one focused commit unless a second commit is
      required to isolate generated documentation.

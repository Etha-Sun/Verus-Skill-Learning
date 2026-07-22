# Experiment Code Review: Qwen Capability Calibration

**Date**: 2026-07-21
**Reviewer**: independent Codex subagent
**Scope**: R040A-R040D calibration implementation before data freeze or GPU deployment

## BLOCKING issues

1. **Selection is biased toward non-canonical variants.** `_canonical_candidates()` chooses the smallest source for each task, not a declared canonical/original variant. On the real manifest with a model-free precheck, the resulting 30 tasks were 18 `no_lemma`, 4 `advanced+no_lemma`, 1 `advanced`, and only 7 `standard`. This does not measure Qwen capability on a representative “original task” distribution.

2. **Leakage assertions are not verified against physical files.** Source hashes are trusted from the manifest rather than recomputed; source paths are derived without containment validation; `selected_exact_*_overlap` and `sealed_content_reads` are hardcoded to zero. A stale or malformed manifest can invalidate exact/near filtering or read outside the intended train directories.

3. **Calibration-source uniqueness is not enforced.** Tasks are deduplicated only by normalized task ID. Two different IDs with the same normalized source can both be selected; `unique_source_count` is reported but never used as a gate.

4. **The required 32,768-token context eligibility/configuration is absent.** Selection does not calculate or record context eligibility, and run manifests do not enforce or record the provider’s actual context limit. Context-ineligible tasks can therefore contaminate the capability map.

5. **Tier/infrastructure logic is not contract-safe.**
   - Lynette timeout/tool failure is not classified as infrastructure failure.
   - A timed-out/context-exhausted run can still contribute to `pass` because pass is checked before infrastructure failure.
   - Missing results are treated as infrastructure failures, and `aggregate_screen()` still writes `r040d_frozen_tiers.json`; an incomplete run can therefore be falsely frozen.
   - Aggregation outputs can be silently overwritten.

6. **The two-stage repetition/freeze protocol is not implemented.** There is no predeclared boundary-candidate selector and no deterministic freeze of three representative tasks per tier. The current path either leaves this manual or runs all 30 tasks three times, diverging from M0.5.

7. **`verified_count` increase is not reliable proof progress.** Lynette permits proof-only additions, so adding an unrelated trivial lemma can increase total verified count without moving the target obligation closer to completion. This can falsely create `near_miss` cases.

## NON-BLOCKING issues

- The inherited “7-token shingles” tokenize code after removing all whitespace, so they are not true Rust lexical-token shingles and can create boundary artifacts.
- Paired verified files are checked for existence but not independently prechecked as valid verified artifacts.
- Size-tertile balancing is reasonable but is not documented in the plan.
- Tests pass with `PYTHONPATH=src`, but current coverage only exercises four happy-path/unit cases.

## Suggested patches/checks

- Select only a predeclared canonical variant, preferably `standard`, or explicitly freeze a variant-stratified sampling contract.
- Resolve every source/verified path, require containment under the expected Anvil/IronKV directory, recompute hashes, and compare them with manifest metadata.
- Enforce exactly 30 tasks, 15/15 groups, 30 unique normalized tasks, and 30 unique normalized sources before writing `DONE`.
- Compute tokenizer-based context eligibility and record model path/hash, context limit, provider configuration, prompt hash, and tool versions.
- Make run outcomes mutually exclusive; include Copilot, Verus, and Lynette failures/timeouts in infrastructure status.
- Refuse frozen aggregation unless all required repetitions exist and validate their task/source/prompt/model hashes; make frozen output directories immutable.
- Implement objective boundary selection plus deterministic three-per-tier freezing before H1/H2.
- Define progress using target-error fingerprints or reduction of relevant Verus obligations; do not accept total `verified_count` increase alone.
- Add adversarial tests for duplicate sources, stale hashes, path traversal/sealed paths, non-standard variant bias, Lynette failure, timeout-plus-valid-candidate, incomplete aggregation, collisions, context eligibility, and artificial verified-count inflation.

## Deployment verdict

**NO-GO** for freezing R040A or launching R040B. Model-free dry-runs remain safe, but the selection and tier-freezing correctness issues must be fixed first.

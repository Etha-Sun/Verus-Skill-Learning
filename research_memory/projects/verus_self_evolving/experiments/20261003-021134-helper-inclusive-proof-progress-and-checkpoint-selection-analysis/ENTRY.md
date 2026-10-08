# Helper-inclusive proof progress and checkpoint selection analysis

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-10-03T02:11:34`
- dataset/split: fixed train40,39 verified successes; no held-out reads
- baseline: preserved target-only progress report and exact original traces
- variant: compiler-resolved target/helper dependency scope; full-candidate gated helper pruning
- metrics: paired target-only/combined platforms, output-token spans, regressions, repeated diagnostic episodes and checkpoint candidates
- leakage controls: hindsight train-only analysis; no API calls, no paid forks, no selector freeze
- stop condition: validated implementation,39 accounted-for reports, case studies and bounded selection proposal

## Commands

```bash
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src python scripts/analyze_train_proof_progress.py \
  --source-root "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/train40-pro-initial-1800s-20261001-KjQXKA" \
  --output-dir "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/train39-helper-progress-20261003-B92hK9" \
  --run-root "$VERUS_SKILL_RUN_ROOT" --verus-bin "$VERUS_BIN" --lynette-bin "$LYNETTE_BIN" \
  --workers 4 --verifier-timeout-seconds 120 --include-helpers \
  --parent-report-root "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/train39-progress-reviewed-20261002-YeOZGq"
# Exact expanded tool paths/hashes and every actual command are in the external manifest/logs.
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src python scripts/summarize_train_proof_progress.py \
  --report-roots "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/train39-helper-progress-20261003-B92hK9" \
    "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/train39-helper-parser-fix-20261003-J4Vbfz" \
  --output-dir "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/train39-helper-reviewed-20261003-EGEcwN" \
  --run-root "$VERUS_SKILL_RUN_ROOT"
```

## Outputs

- preflight: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/helper-progress-smoke-20261003-we3F9F/`
- full run: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/train39-helper-progress-20261003-B92hK9/`
- macro/external-body parser recovery: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/train39-helper-parser-fix-20261003-J4Vbfz/`
- reviewed consolidation: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/train39-helper-reviewed-20261003-EGEcwN/`
- logs: actual verifier/IR output and per-task provenance
- metrics: old and new views paired on common final references
- manifest: exact input, parent report, code and tool hashes

## Results

Implementation tested:110 passed,13 subtests passed. Full local reanalysis is
complete:39 curves,368 calls,10 tasks/25 related helpers and11 excluded changed
proofs. See RESULTS.md for paired primary/supplemental statistics, CASE_STUDIES.md
for contrasts and CHECKPOINT_PROPOSAL.md for the unactivated three-point proposal.
All new deletion gates and latest-parser scopes audited; no paid inference.

## Interpretation

The user's long-platform-start heuristic is a retained comparator, not rejected
in advance. No offline proxy establishes hint usefulness or causal token savings.

## Next Action

User review of candidate prioritization and context-prefix fallback. Later causal
hint/no-hint experiments are required to compare value; none started here.

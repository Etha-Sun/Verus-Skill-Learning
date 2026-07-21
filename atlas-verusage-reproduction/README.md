# ATLAS × VeruSAGE reproduction

This directory reproduces the ATLAS adaptive failure-taxonomy pipeline on a
small, task-disjoint sample of the local VeruSAGE repair corpus.

The four `all_batch_results-cyy-*` directories are inputs only. The adapter
rejects output paths inside any raw-data directory. All generated JSONL,
manifests, taxonomies, logs, and diagnoses belong below
`VERUS_SKILL_RUN_ROOT`, outside this repository.

## Scope

1. Convert complete VeruSAGE repair runs to ATLAS's unified trace schema.
2. Induce system-level (A), role-specific (B), and Verus-domain (C) codes with
   ATLAS's vendored eight-step pipeline.
3. Preserve an eval split with normalized task ids absent from taxonomy
   induction.

The adapter renders evidence-bearing attempt summaries rather than copying
entire logs. It distinguishes attempt-local acceptance from the task-level
`results.csv` outcome and records every selected source log plus SHA-256 in the
manifest.

## Commands

```bash
PYTHONPATH=src \
  python3 atlas-verusage-reproduction/prepare_traces.py \
  --data-root "${VERUS_SKILL_DATA_ROOT}" \
  --out "${VERUS_SKILL_RUN_ROOT}/atlas/pilot_v1/input"

PYTHONPATH="src:${ATLAS_ROOT}" \
  python3 atlas-verusage-reproduction/run_taxonomy.py \
  --traces "${VERUS_SKILL_RUN_ROOT}/atlas/pilot_v1/input/train.jsonl" \
  --out "${VERUS_SKILL_RUN_ROOT}/atlas/pilot_v1/taxonomy" \
  --model gpt-5.6-sol \
  --transport codex-cli \
  --reasoning-effort high

PYTHONPATH="src:${ATLAS_ROOT}:atlas-verusage-reproduction" \
  python3 -m unittest discover \
  -s atlas-verusage-reproduction -p 'test_*.py' -v
```

`ATLAS_ROOT` points to a separately pinned external ATLAS checkout. Keep its
machine-local absolute path in the ignored `.env`; do not commit it.

# R040 leakage-safe stratified train trace selection

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-20T16:42:28`
- status: `done`
- dataset/split: 3,341-row effective train manifest; Anvil and IronKV only
- baseline: no sampling; full effective-train candidate pool
- variant: deterministic 30-trace stratified diversity selection
- metrics: unique task/source counts, model/directory/variant/motif/error coverage
- leakage controls: reject non-train directories before log reads; sealed reads 0
- stop condition: 30 non-null verified artifacts, unique normalized tasks and
  sources, all files present, balanced directory/model strata

## Commands

```bash
PYTHONPATH=src python3 -m verus_self_evolve.handsoff_m1 \
  --manifest runs/handsoff_distill_20260719/m0/effective_corpus_manifest.jsonl \
  --corpus-root ../claude_sonnet_gpt5 \
  --out-dir runs/handsoff_distill_20260719/m1/r040_selection_attempt3 \
  --per-stratum 3
```

## Outputs

- run directory: `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m1/r040_selection_attempt3/`
- logs: `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m1/RUNLOG.md`
- metrics: `selection_summary.json`
- manifest: `selected_traces.jsonl`, `run_manifest.json`

## Results

| metric | result |
|---|---:|
| selected traces | 30 |
| unique normalized tasks / sources | 30 / 30 |
| Anvil / IronKV | 15 / 15 |
| each of five known models | 6 |
| represented corpus variants | 5 / 5 |
| selected log + verified path audit | 30 / 30 PASS |
| sealed content reads | 0 |

## Interpretation

R040 satisfies its selection contract. The set is balanced across project
directory and frontier model, de-duplicated by task and normalized source, and
contains only rows with actual paired verified files. Motif/error-family labels
are keyword heuristics used to diversify sampling; they are not evidence of
taxonomy accuracy or downstream agent benefit. Attempts 1-2 remain preserved:
attempt1 exposed a serializer typo, and attempt2 exposed a null-path success
predicate bug. Attempt3 is canonical with selected JSONL SHA-256
`fa192540148c6ad5a82fe239ca977aaa8c0998c2483717ca8e46f23caa32281b`.

## Next Action

R041: distill a <=800-token train-only H2 prompt and a length-controlled H1
generic prompt, recording source trace IDs, prompt hashes, and distillation
cost separately from inference cost.

# ATLAS adaptive failure taxonomy reproduction for VeruSAGE traces

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-11T09:51:53`
- dataset/split: local 2,996-trace snapshot; taxonomy train 40 unique tasks;
  reserved eval 12 unique tasks; normalized-task overlap 0
- baseline: ATLAS commit `afbf010117ce`
- variant: compact VeruSAGE adapter + Codex CLI `gpt-5.6-sol/high`
- metrics: 28 final codes (A=6, B=11, C=11), 36/36 successful calls,
  Step-7 structural violations=0
- leakage controls: group by normalized task across models; one trace per task;
  reserved eval tasks excluded from induction
- stop condition: taxonomy induction complete; comparison gate remains open until
  held-out diagnosis and evidence audit

## Commands

```bash
PYTHONPATH=../verus-self-evolve-scaffold/src python3 prepare_traces.py \
  --data-root .. --out runs/pilot_v1/input_v2

PYTHONPATH=../external_repos/ATLAS python3 run_taxonomy.py \
  --traces runs/pilot_v1/input_v2/train.jsonl \
  --out runs/pilot_v1/taxonomy_sol_high_v2 \
  --model gpt-5.6-sol --transport codex-cli \
  --reasoning-effort high --max-codes 24 --timeout 900
```

## Outputs

- run directory: `atlas-verusage-reproduction/runs/pilot_v1/`
- logs: `taxonomy_sol_high_v2/codex_calls/`
- metrics: `json/metric_contract.json`
- manifest: `input_v2/manifest.json`
- report: `REPORT.md`

## Results

| metric | result |
|---|---:|
| final taxonomy codes | 28 |
| system / role / domain codes | 6 / 11 / 11 |
| Codex call success | 36 / 36 |
| train/eval task overlap | 0 |
| Step-7 structural violations | 0 |

## Interpretation

The result supports feasibility: ATLAS can induce a compact, Verus-specific
failure vocabulary from this corpus. It does not yet support diagnosis accuracy
or repair-improvement claims because there are no human code labels and no
downstream frozen-taxonomy A/B run.

## Next Action

Run cross-model held-out diagnosis on the 8 FAILED/TIMEOUT eval traces, manually
audit evidence spans, then decide whether to run a frozen-taxonomy prompt-level
repair A/B experiment.

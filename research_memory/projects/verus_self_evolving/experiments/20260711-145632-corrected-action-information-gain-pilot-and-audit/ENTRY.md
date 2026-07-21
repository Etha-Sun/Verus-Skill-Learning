# corrected action information gain pilot and audit

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-11T14:56:32`
- dataset/split: 3 verified Claude hands-on traces, 7 early/middle/late states; engineering pilot only, no held-out claim.
- baseline: QwQ-32B normalized probability of the observed VeruSAGE action under the current state.
- variant: the same state plus one artifact/control.
- metrics: decision PMI bits, observed-action probability/rank, entropy change, exact-intervention-token density, paired state differences, trace-cluster bootstrap summaries.
- leakage controls: action context excludes current action and final proof; raw data read only; v2 freezes a 22-action ontology and records acceptance/source provenance.
- stop condition: do not run patch/full-proof or scale if trace rationale does not directionally beat shuffled and irrelevant controls.

## Commands

```bash
cd verus-self-evolve-scaffold
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m verus_self_evolve.cli ig-probe-analyze \
  --aggregates runs/corrected_ig_20260711/r017_seven_states/aggregates.jsonl \
  --out-dir runs/corrected_ig_20260711/r017_seven_states/analysis
```

## Outputs

- run directory: `verus-self-evolve-scaffold/runs/corrected_ig_20260711/r017_seven_states/`
- corrected-v2 manifest: `verus-self-evolve-scaffold/runs/corrected_ig_20260711/r017_manifest_v2/`
- corrected-v2 cases: `verus-self-evolve-scaffold/runs/corrected_ig_20260711/scoring_cases_v2_accepted_ontology.jsonl`
- results: `refine-logs/EXPERIMENT_RESULTS_20260711_145502.md`
- audit: `refine-logs/EXPERIMENT_AUDIT_20260711_145502.md`
- manifest: `MANIFEST.md`

## Results

| comparison | mean trace-minus-control bits | trace wins |
|---|---:|---:|
| trace rationale vs shuffled | 0.0449 | 3/7 |
| trace rationale vs irrelevant | -0.0748 | 2/7 |
| trace rationale vs generic | 0.8014 | 5/7 |
| trace rationale vs word-count neutral | 0.7497 | 6/7 |

## Interpretation

The scorer implementation is feasible and its PMI/entropy mathematics passed independent recomputation. The current artifact-quality hypothesis is not supported: irrelevant text has higher mean PMI than trace rationale, and shuffled rationale is nearly tied. One of seven original action labels was rejected, so R017 is not a successful-action evaluation. No skill-quality or downstream claim is allowed.

## Next Action

Improve artifact generation using actual trajectory evidence, then score the six accepted v2 action states against randomized tokenizer-matched controls. Keep full-proof and patch targets in the plan, but reopen them only after the action artifact gate passes.

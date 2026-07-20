# Offline Eval Summary

Command:

```bash
PYTHONPATH=src python3 -m verus_self_evolve.cli run \
  --out "${VERUS_SKILL_RUN_ROOT}/offline-replay-baseline"
```

Dataset:

- traces: 2,996
- verified: 1,691
- nonverified: 1,305
- effective total tokens: 1,524,386,760

Retained compact artifacts:

- `results/offline-replay-baseline/summary.json`
- `results/offline-replay-baseline/policy_ablation.csv`
- `results/offline-replay-baseline/report.md`

The complete generated run remains outside Git under
`VERUS_SKILL_RUN_ROOT`.

Main result:

| policy_level | selected_top_k | union_covered_failed | union_saved_failed_tokens | false_stop_rate | peer_diff_rate |
|---|---:|---:|---:|---:|---:|
| generic | 20 | 1,038 | 800,760,044 | 0.112951 | 0.748705 |
| project | 20 | 539 | 548,995,746 | 0.039030 | 0.748252 |
| motif | 20 | 227 | 309,382,084 | 0.005322 | 0.777778 |

Interpretation:

- Generic rules cover the largest failed-token mass but have high false-stop
  risk.
- Project-aware rules reduce false-stop risk while retaining large token
  coverage.
- Motif-aware rules are the safest in this run and have the strongest
  peer-action disagreement signal, supporting the need for Verus-specific
  decision policy rather than only generic repetition gating.

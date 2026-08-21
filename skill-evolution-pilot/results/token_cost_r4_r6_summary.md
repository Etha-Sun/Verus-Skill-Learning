# Token-Cost Evolution R4-R6 Summary

## Scope

R4-R6 tested whether textual solver skills derived from the agent-design ideas
in `tmp.txt` could reduce primary uncached Expected Tokens to Success on the
existing frozen four-task matrix. The solver model, prompt, tools, task set,
and 600-second budget were unchanged.

## Results

| Condition | Best skill | Valid matrix | Solved | ETtS | Delta vs H0 |
|---|---|---:|---:|---:|---:|
| H0 | none | yes | 4/4 | 52,350.0 | - |
| R1 prior best | `bounded-exploration-gate` | yes | 4/4 | 51,497.0 | -853.0 (-1.63%) |
| R4 | `zero-ceremony-direct` | yes | 4/4 | 59,032.0 | +6,682.0 (+12.76%) |
| R5 | `backward-contract-frontier` | yes | 4/4 | 52,013.5 | -336.5 (-0.64%) |
| R6 | `micro-direct-kernel` | yes | 4/4 | 51,881.0 | -469.0 (-0.90%) |

R6 token decomposition:

| Condition | Uncached input | Output | Total |
|---|---:|---:|---:|
| H0 | 182,930 | 26,470 | 209,400 |
| R6 `micro-direct-kernel` | 180,663 | 26,861 | 207,524 |
| Delta | -2,267 | +391 | -1,876 |

R6 per-task primary uncached tokens:

| Task class | H0 | R6 best | Delta |
|---|---:|---:|---:|
| stable pass | 25,555 | 31,140 | +5,585 |
| stable closest failure | 71,816 | 66,859 | -4,957 |
| unstable | 32,784 | 33,013 | +229 |
| hard solved | 79,245 | 76,512 | -2,733 |

## Interpretation

R5 and R6 each produced a complete four-task candidate slightly below H0, but
R6 remained 384 tokens above the earlier R1 best. The effects are strongly
task-dependent: the R6 skill helps the two longer tasks while taxing the
direct task. This supports testing conditional routing or a literal no-skill
path; it does not show that universal skill injection is reliably efficient.

The R6 aggressive candidate had verifier-safe final code on all four tasks,
but the closest-task trace had no terminal usage event at the timeout
boundary. It is excluded from token comparison.

These are single trajectories on the evolution tasks. The sub-1% deltas are
smaller than observed H0 variability and are not stable or held-out evidence.

## Operational caveats

- R4's first meta call and R6's first meta call ended in provider stalls. Their
  immutable failed directories were retained; successful retries used the same
  inputs and configuration.
- Two R6 batch coordinators briefly overlapped. Output-directory exclusivity
  prevented duplicate task execution. The canonical summary reads the 12
  independent ledgers directly.
- Raw and sealed datasets were read-only. Generated traces remain only under
  `VERUS_SKILL_RUN_ROOT`.

## External artifacts

- `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r4-matrix-20260726/token_matrix_summary.json`
- `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r5-matrix-20260726/token_matrix_summary.json`
- `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r6-matrix-20260726/token_matrix_summary.json`
- `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/gpt55-canonical-log-20260726/codex_events.raw.jsonl`
- `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/gpt55-canonical-log-20260726/verusage_transcript.log`

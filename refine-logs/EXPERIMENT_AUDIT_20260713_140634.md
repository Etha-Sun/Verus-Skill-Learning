# Experiment Audit

**Verdict: PASS_WITH_LIMITATIONS**  
**Predeclared GO decision: FAIL — STOP**

The artifacts and arithmetic are internally consistent, with no evidence of fabricated results or forbidden future-proof leakage. However, the evidence artifact fails every predeclared GO requirement. Patch/full-proof scoring and scale-up are therefore not permitted under the plan.

## Findings, ordered by severity

1. **HIGH — The efficacy gate fails.** The independently recomputed mean specific gain is **−0.207868 bits**, median **−0.204672 bits**, with only **2/6** positive states. Evidence wins against `cross_trace_same_error`, `block_shuffled`, and `irrelevant_archive` in **3/6, 2/6, and 2/6** states, respectively—not the required 4/6. This matches the stored negative gate verdict ([plan](<workspace>/refine-logs/EXPERIMENT_PLAN_20260713_000845.md:44), [analysis](<workspace>/verus-self-evolve-scaffold/runs/control_null_ig_20260713/r025_six_states/analysis/analysis_summary.json:150)).

2. **MEDIUM — “Decision PMI” is only a forced-choice conditional proxy.** The code correctly applies log-sum-exp normalization across 22 options ([logprob_scorer.py](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/logprob_scorer.py:53)), and normalized probabilities sum to 1 within \(6.7\times10^{-16}\). But the total raw next-token mass assigned to A–V is only **\(5.00\times10^{-12}\)–\(3.96\times10^{-10}\)**. All six evidence cases have negative raw target-token IG, averaging **−2.279571 bits**, while conditional decision PMI averages **−0.192211 bits**. Thus these values cannot be described as the model’s unconstrained next-action probability or ordinary action PMI—only as probabilities conditioned on emitting one of the 22 option letters.

3. **MEDIUM — Limited scope and residual selection/history confounding.** The pilot covers only **6 states, 3 traces, 4 observed actions, one model, and one option permutation per state**. All traces were selected from eventually verified runs ([ig_probe.py](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py:305)). In 3/6 later states, the current target action also appears among permitted prior actions in the evidence artifact. That is decision-time information rather than forbidden future leakage, but it prevents clean attribution solely to verifier-state semantics.

4. **LOW — Supplied summary paths are inaccurate.** Neither requested `scoring_summary.json` exists. The corresponding files are [r024 `summary.json`](<workspace>/verus-self-evolve-scaffold/runs/control_null_ig_20260713/r024_one_state/summary.json:1) and [r025 `summary.json`](<workspace>/verus-self-evolve-scaffold/runs/control_null_ig_20260713/r025_six_states/summary.json:1). Their recorded hashes match the existing result files, so this is a packaging/path defect, not a phantom-result defect.

## Independently recomputed checks

- Cases: **42 = 6 states × 7 conditions**; each condition has six rows. R024 contains 7 cases.
- Matrix: evidence, five token-matched null controls, and `empty_container`; empty is correctly excluded from the null mean.
- Exact token deltas: **124, 157, 125, 124, 144, 160** by state. All six non-empty conditions match exactly within each state; total per condition is **834 tokens**. `empty_container` adds 3 tokens.
- Live tokenizer recomputation from the stored contexts found **0/42 mismatches**.
- Token scoring: **1,848 = 42×2×22** R025 token rows; every A–V target is exactly one token and `prob = exp(logprob)`.
- Evidence PMI: mean **−0.192211 bits**, positive in **3/6** states.
- Specific gains by state: **−0.484416, −0.392865, −1.111359, +0.652938, +0.104974, −0.016479 bits**.
- The mechanical integrity gate passes: complete matrices, 22 candidates, locally accepted labels, identical within-state option maps, matching serialized targets, `chat_direct`, and exact intervention deltas ([gate implementation](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_analysis.py:177)).
- Artifact construction uses the pre-attempt code, current error, and earlier actions/errors; the evidence path does not read the final proof or current target action ([prefix construction](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py:273), [evidence construction](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py:726)).

## Permissible claims

- The 22-way forced-choice scoring pipeline is mechanically consistent and exactly token-matched.
- No forbidden current-target or final-proof input was found in evidence construction.
- In this six-state pilot, the evidence artifact **did not outperform the matched null controls**.
- The predeclared result is **STOP**: revise artifact construction before patch/full-proof scoring or expansion.

Not permissible: state-specific information gain, improved action selection, superiority to controls, held-out generalization, causal benefit, or interpreting normalized option scores as the model’s natural action distribution.

The skill-mandated cross-agent reviewer could not be started because the reviewer interface failed; this is a fresh single-agent recomputation. No files were modified because the workspace is read-only.
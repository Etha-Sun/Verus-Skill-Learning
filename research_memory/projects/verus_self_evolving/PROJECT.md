# Project: Verus Self-Evolving Proof Repair

## One-Line Goal

Mine Verus proof-repair trajectories into verifier-grounded skills, skeletons,
and structured decision rules that improve repair action selection without
polluting raw data.

## Current Research Claim

The current repair system has Verus-specific tools/actions but lacks a
Verus-specific learned decision policy. Historical traces can be used to mine
candidate rules, rationales, counterexamples, and skills. The newest direction
scores these artifacts by information gain: whether adding the artifact to a
trajectory prefix increases the likelihood of the final verified proof. Final
claims still require split-aware evaluation to avoid overfitting and data
leakage.

## Canonical Artifacts

- Initial trace analysis:
  `analysis_verusage_trace_ideas_20260624/`
- Meeting-grounded auto research:
  `analysis_verusage_trace_ideas_20260624/auto_research_20260628/`
- Executable scaffold repository:
  `verus-self-evolve-scaffold/`
- Scaffold run outputs:
  `verus-self-evolve-scaffold/runs/latest/`

## Raw Data Contract

Raw data directories are read-only:

- `all_batch_results-cyy-claude/`
- `all_batch_results-cyy-claude-s4/`
- `all_batch_results-cyy-gpt5/`
- `all_batch_results-cyy-o4mini/`

Derived outputs must be written to `research_memory/`, an experiment repository,
or a new run directory, never into raw data directories.

## Current Open Questions

1. How should rule mining be split to avoid exact-task and cross-model leakage?
2. Can motif-aware rules preserve solved rate better than generic repetition
   rules in live reruns?
3. Which Verus-specific signals should be promoted first: lemma dependency,
   quantifier trigger, temporal/TLA motif, or project-specific context policy?
4. Does proof information gain reliably separate useful rationales/skills from
   irrelevant or misleading controls?
5. Should evolved skills be evaluated directly in prompts, or indirectly by
   generating counterexample-like rationales that are then scored by proof IG?

## Next Recommended Entries

- `experiments`: `information_gain_reward_probe`.
- `experiments`: split-aware rule replay evaluation.
- `decisions`: decide leakage-safe evaluation contract.
- `ideas`: selected rule DSL and self-evolution loop design.

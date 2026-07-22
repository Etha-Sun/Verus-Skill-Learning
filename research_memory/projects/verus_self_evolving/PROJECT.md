# Project: Verus Self-Evolving Proof Repair

## One-Line Goal

Mine Verus proof-repair trajectories into verifier-grounded skills, skeletons,
and structured decision rules that improve repair action selection without
polluting raw data.

## Current Research Claim

The current repair system has Verus-specific tools/actions but lacks a
validated Verus-specific learned decision policy. Historical traces can be
used to mine candidate rules, rationales, counterexamples, and skills.
Information gain can rank or diagnose these artifacts as a secondary offline
proxy. It does not establish downstream solved-rate or token-efficiency gains;
those claims require leakage-safe live evaluation.

## Canonical Artifacts

- Initial trace analysis:
  `analysis_verusage_trace_ideas_20260624/`
- Meeting-grounded auto research:
  `analysis_verusage_trace_ideas_20260624/auto_research_20260628/`
- Executable code and documentation:
  `src/` and `docs/`
- Generated run outputs:
  `VERUS_SKILL_RUN_ROOT`

## Raw Data Contract

Raw data directories below `VERUS_SKILL_DATA_ROOT` are read-only:

- `all_batch_results-cyy-claude/`
- `all_batch_results-cyy-claude-s4/`
- `all_batch_results-cyy-gpt5/`
- `all_batch_results-cyy-o4mini/`

Generated experiment outputs must be written below `VERUS_SKILL_RUN_ROOT`,
never into raw data directories or the repository. Keep only reviewed compact
summaries and pointers in `research_memory/`.

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

- `experiments`: monitor the active 18 R040C H0 repetitions, then freeze one
  stable pass, closest-failure, and stalled qualitative case.
- `experiments`: R041 H1/H2 prompts are frozen; prepare the 27-record R041A
  manifest after R040D.
- `experiments`: run leakage-safe held-out live H0/H1/H2 evaluation.
- `decisions`: promote, redesign, or stop local transfer based on frozen-tier
  diagnostics without treating selected cases as method evidence.

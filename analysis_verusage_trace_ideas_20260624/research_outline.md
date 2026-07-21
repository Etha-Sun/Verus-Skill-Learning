# Research Outline

## Executive Summary

Verusage traces suggest the highest-value route is not another generic repair action. The main opportunity is a controller/data improvement: convert existing successful and failed trajectories into a compact proof-skeleton and loop-memory system. This should improve capability on hard project families and reduce token waste from repeated full-context prompting.

## Codebase / Data Analysis

The workspace is a result repository with:

- early `result-*` directories containing repair candidates, diffs, summaries, checkpoints, and some reasoning;
- later `all_batch_results-*` directories containing per-call prompts/outputs, reasoning, repair logs, and per-model batch summaries;
- `claude_sonnet_gpt5/` with cross-model project results and script outputs.

No original data was modified. New artifacts are only in this analysis folder.

## KPIs

- Verified rate under 20-minute cap.
- Total tokens and non-verified average tokens.
- Number of repeated same-action loops.
- Skeleton retrieval hit rate.
- False-stop rate of repetition gate.

## Five Actionable Directions

1. **Trace skeleton cache**  
   Distill successful traces into reusable proof plans.

2. **Repetition gate**  
   Stop repeated action/error loops and force route changes.

3. **Project-family context profiles**  
   Compress prompts differently for `AC`, `NR`, `OS`, etc.

4. **Final-verification-aware local reward**  
   Penalize local fixes that create persistent downstream assertion failures.

5. **Action router from trace features**  
   Learn or hand-code priors after skeleton/error signatures are stable.

## Recommended Next Experiment

Implement an offline replay analysis before touching the live repair agent:

1. Parse all `verus-repair.log` files into attempt records.
2. Normalize error signatures.
3. Simulate repetition gates at thresholds 2, 3, and 4.
4. Extract skeletons from verified traces and `fix-v*-success-*` files.
5. Evaluate retrieval hit rate on heldout high-token failures.

If offline replay is favorable, run a small online smoke on high-token `AC/NR/OS` failures.


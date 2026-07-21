# Idea Node Plan

## Bottleneck

Verusage agents waste tokens by repeating low-value repair actions on stable verifier errors and by failing to reuse successful proof structure across models/runs.

## Candidate Families

- live: trace-distilled proof skeleton cache;
- live: repetition gate / loop-aware action router;
- component: project-family prompt compaction;
- deferred: final-verification-aware reward shaping;
- deferred: learned action policy after trace signatures are stable.

## Selection Gate

Select a direction only if it:

- uses only current Verusage traces and existing verifier outcomes;
- can be falsified offline before expensive runs;
- targets both verified rate and token cost;
- avoids exact-task leakage for model-capability evaluation.

## Current Outcome

Selected `verusage_trace_skeleton_gate_20260624`.

Next stage: implement offline replay and skeleton extraction before live repair-agent changes.


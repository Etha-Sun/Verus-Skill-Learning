# Candidate Frontier

## Raw Slate

1. **Trace-distilled proof skeleton cache**  
   Extract successful traces into compact proof plans keyed by project, file family, target lemma/function, error type, helper-lemma graph, and final patch motif.

2. **Repetition gate / loop-aware action router**  
   Detect repeated `(error signature, action, local outcome)` cycles and force a route change, proof-plan retrieval, smaller context, or early stop.

3. **Project-family prompt compaction**  
   Build separate prompt policies for `AC`, `NR`, `OS`, `MA`, `AL`, etc.; replace full-code replay with focused target slices and helper lemma summaries.

4. **Final-verification-aware reward shaping**  
   Penalize accepted local repairs that introduce persistent downstream `AssertFail` loops; reward monotonic progress toward `VERIFIED`, not target-error removal alone.

5. **Action-policy learner from existing traces**  
   Train a lightweight router over local trace features: project, error type, function name, known lemmas, previous action failures, and token budget.

6. **Cross-model proof distillation set**  
   Use cases where one model succeeded and others failed to produce compact teacher proof plans for heldout-family evaluation.

7. **Generic vstd retrieval replacement for Verusage helper-lemma retrieval**  
   Index local successful helper lemmas and external-body lemmas by spec-shape rather than token overlap with vstd examples.

8. **Budgeted two-stage repair**  
   First ask for proof diagnosis and skeleton only; generate code only if the skeleton names concrete lemmas/witnesses/cases.

## Serious Frontier

| candidate | relevance | feasibility | upside | token-saving potential | risk | verdict |
|---|---:|---:|---:|---:|---|---|
| trace skeleton cache + repetition gate | high | high | high | high | leakage if evaluated exact-task | select |
| project-family prompt compaction | high | medium | medium-high | high | needs careful slicer | defer as component |
| final-verification-aware reward shaping | high | medium | medium | medium | requires progress metric design | defer |
| standalone action-policy learner | medium | medium | medium | medium | may overfit current logs | reject as first step |

## Selected

Select **trace-distilled proof skeleton cache + repetition gate** as the next executable route.

Why it wins:

- It directly targets the largest observed waste: repeated high-token failures.
- It uses Verusage-specific evidence already present in the data.
- It can be falsified offline before expensive new model runs.
- It improves both capability and cost: proof skeletons can guide hard tasks, while repetition gates stop known-bad loops.

## Deferred

- Project-family prompt compaction should be implemented as part of the selected route once skeleton keys are defined.
- Final-verification-aware reward shaping should follow after measuring whether local-success loops remain.

## Rejected For Now

- Pure action-policy learning is too likely to learn superficial correlations without first defining stable trace signatures.
- More generic retrieval examples are unlikely to fix AC/NR/OS failures because the sampled prompts already show generic examples missing the project-specific temporal/spec structure.


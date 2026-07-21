# Objective Contract

## Real Target

Improve Verusage agent performance under the existing dataset and verifier contract:

- Higher end-to-end `VERIFIED` rate.
- Lower total `input_tokens + output_tokens`.
- Lower wall-clock time under the same repair budget.
- No new dataset, no human labels, no weakening of Verus checks, no `assume`/cheat-based success.

## Trusted Proxies

- `all_batch_results-*/all_results_with_breakdown_20min.csv`: per-model status, time, tokens, project.
- `*_analysis_results.csv`: task-level verified flag, steps, action traces, added lines, versions.
- `*_action_counts.csv`: action usage and, where present, success counts.
- `verus-repair.log`: attempt-level errors, selected agents/actions, accepted/rejected candidates, LLM token calls.
- `llm-prompts/*.txt` and `reasoning/*.txt`: prompt size, previous-attempt content, reasoning plans.

## False Progress Signals

- Local action success without final `VERIFIED`. Logs show `fix-v*-success-*` can coexist with final failed batch status.
- Reducing output tokens while input-token replay of full code and prior attempts remains huge.
- More attempts or more candidates without reduction in repeated error signatures.
- Better action-level success counts for an action that only moves the failure from `PostCondFail` to repeated `AssertFail`.
- Exact-task memorization presented as model capability. Exact retrieval is useful operationally, but model-training claims require heldout task or family splits.

## Hard Constraints

- Keep Verusage tasks and verifier unchanged.
- Do not train on heldout target patches if evaluating generalization.
- Do not introduce leakage-prone labels such as final patch text into heldout prompts.
- Prefer mechanisms that can be tested offline from existing traces before running expensive new batches.

## Contribution Frame

Expected contribution type: **Capability + Efficiency**.

Problem importance: Verusage has repository-scale formal verification tasks where failed agents can spend millions of tokens on repeated repair loops.

Main bottleneck: the agent does not compactly reuse successful proof structure or negative loop evidence from its own traces.

Intended increment: reduce high-cost failed loops while increasing success on AC/NR/OS-style tasks by routing earlier to trace-derived proof skeletons.


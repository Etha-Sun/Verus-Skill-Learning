# Objective Contract

## Problem anchor

Improve a frozen DeepSeek V4 Pro agent's ability to extract useful, transferable experience from long VeruSAGE repair traces, with downstream budgeted Verus-plus-Lynette success and efficiency as the goals. Start with the existing train40 and validation20. Evaluate Verus-specific claims on VeruSAGE; a claim of general code-generation benefit requires a later code-generation benchmark.

## Success and false progress

- Primary: same-harness paired budgeted dual-pass solved rate on tasks excluded from all experience-learning ancestry.
- Efficiency: aggregate input/output tokens, cached/uncached usage, actor time, API cost, timeouts over all attempted episodes. Report analysis/replay costs separately and jointly, with amortization assumptions.
- Mechanism diagnostics: evidence extraction correctness, applicability precision, unsupported statements, omitted helper/code changes, trace coverage. These do not prove downstream gain.
- False progress: more cards/branches, higher reviewer score, longer or shorter summaries, card-read counts, final-answer similarity, offline information gain, extra retries/compute, or source-task continuation success.
- Constraints: existing frozen split/tasks, immutable raw/sealed data, fixed actor/model/version/budget, unchanged task specifications, held-out ancestry controls, no test-driven edits, no silently truncated traces.
- Scope: VeruSAGE first. Because the selected architecture could apply to code with tests, a code-generation follow-up is required if the final mechanism remains generic; do not evade this user requirement by merely narrowing claimed wording.

## Competing explanations

H1: Long-context presentation obscures important state transitions.
H2: Consolidation overgeneralizes single-task evidence regardless of context length.
H3: Useful rules are extracted but poorly applied by the runtime agent.
H4: Model capability or toolchain compatibility dominates; skill analysis cannot bridge it under the current budget.

No explanation is currently established as the main bottleneck.

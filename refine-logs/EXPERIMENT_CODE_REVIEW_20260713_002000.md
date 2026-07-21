Verdict: **DO_NOT_DEPLOY**. The prepared cases pass several structural checks, but the QwQ scoring target is semantically wrong and the controls/gate cannot support the planned claim.

## BLOCKING issues

1. **The scorer measures the first QwQ reasoning token, not the selected action.**

   `_context_target_ids()` applies QwQ’s chat template and then appends `A`–`V` directly ([logprob_scorer.py:39](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/logprob_scorer.py:39), [logprob_scorer.py:194](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/logprob_scorer.py:194)). QwQ’s template ends the generation prompt with:

   ```text
   <|im_start|>assistant
   <think>
   ```

   Therefore the 22 scores are \(P(A\ldots V\mid\text{start of think block})\), not probabilities of the eventual answer after reasoning. The softmax is mathematically valid but is not an action distribution. This invalidates PMI, entropy, rank, specific gain, and the gate.

2. **The concrete controls contain major uncontrolled text-quality confounds.**

   - Planned `irrelevant_style` is proof-unrelated code-editing advice, but the implementation uses long prose about a municipal archive ([plan:33](<workspace>/refine-logs/EXPERIMENT_PLAN_20260713_000845.md:33), [ig_probe.py:816](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py:816)).
   - Exact-length matching pads controls using repeated words such as `" neutral"` ([ig_probe.py:978](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py:978)). In the prepared cases, **12/30 non-empty control rows contain this padding**, sometimes 20–58 repetitions. Evidence versus control can therefore measure fluency/repetition toxicity.
   - `counterfactual_error` changes only the obligation-class label while retaining the real verifier text and code ([ig_probe.py:726](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py:726), [ig_probe.py:815](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py:815)). It does not replace the verifier diagnosis as planned.
   - For `9b4e5f23d82c68a1:late-a11`, `cross_trace_same_error` and `cross_trace_any` are identical, so that null source is double-weighted.

   Because all five controls enter the null mean, these are not cosmetic problems.

3. **The quality gate can pass an incomplete or integrity-invalid run.**

   Missing controls are silently skipped ([ig_analysis.py:109](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_analysis.py:109)); specific gain then averages however many controls remain. The gate derives its threshold from the observed state count rather than requiring exactly six states ([ig_analysis.py:188](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_analysis.py:188)).

   It never requires:

   - exactly 6 states × 5 null controls;
   - 22 candidates per row;
   - accepted targets;
   - identical option maps within state;
   - exact intervention-token matching;
   - complete decisive-control coverage per state.

   Thus `artifact_quality_gate_pass` can be true without satisfying the experiment plan.

4. **Chat configuration can silently change at GPU execution.**

   Cases were matched with `prompt_format: chat` ([summary:28](<workspace>/verus-self-evolve-scaffold/runs/control_null_ig_20260713/action_cases.jsonl.summary.json:28)), but the scoring CLI defaults to `raw` ([logprob_scorer.py:525](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/logprob_scorer.py:525)). Cases do not carry an enforced prompt format, and scoring does not compare actual versus prepared intervention counts.

5. **The plan’s reproducibility contract is not implemented.**

   The summary records paths but not the required case, ontology, tokenizer-config, or aggregate SHA256 values ([plan:67](<workspace>/refine-logs/EXPERIMENT_PLAN_20260713_000845.md:67)). Scorer output likewise does not generate them. Additionally, the reviewed implementation and tests are untracked relative to commit `eaca019`, so that commit does not identify the executed code.

## NON-BLOCKING issues

- “Accepted” is honest only as **VeruSAGE local acceptance**, not improvement or optimality. All six selected rows are genuinely marked accepted in their source logs, but one selected action was accepted with “Fix the target error by 0” ([source log:1497](<workspace>/all_batch_results-cyy-claude/results-batch_001/o-AC__vreplicaset_controller__proof__helper_lemmas__vrs_rely_condition_equivalent_to_lifted_vrs_rely_condition-20251130-194425/verus-repair.log:1497)). The plan’s caveat makes this labeling acceptable.
- `cross_trace_same_error` silently falls back to arbitrary cross-trace evidence when no matching error exists ([ig_probe.py:1007](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py:1007)). It did not mislabel the current six states, but should be explicit before scaling.
- The summary’s `observed_action_count: 4` means four unique labels, not six observed state/action pairs; state and trace counts are omitted.
- Tests do not cover the real QwQ template, full gate completeness, control semantics, or output hashes.

## Checks that passed

- No current-action or final-proof leakage was found in the six evidence artifacts. Evidence construction reads current prefix code, current error, score, and prior history; action cases contain only `action_primary`.
- All `cross_trace_same_error` sources are from different traces with matching error types.
- All **36 non-empty artifact rows** exactly match the evidence intervention delta under the actual QwQ chat template. Empty-container rows correctly add only three tokens and are excluded from the null mean.
- Every state has one reproducible SHA256-seeded permutation shared by all seven artifacts; regenerated mappings match the cases.
- Every case has exactly 22 options, zero reported OOV actions, correct option-to-observed-action mapping, and `A`–`V` are each one QwQ tokenizer token.
- The 22-way softmax implementation and specific-gain formula are correct conditional on valid action scores and a complete control matrix.
- Fourteen unit tests passed. The filesystem-based analysis test could not create a temporary directory under the read-only constraint; an equivalent in-memory specific-gain check passed.

No files were modified.
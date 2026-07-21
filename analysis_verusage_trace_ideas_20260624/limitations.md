# Limitations And Bottlenecks

## L1. Looping On Stable Error Signatures

Symptom: many logs spend 20 attempts on one dominant error/action pair.

Evidence: 1,010 logs repeat the same primary action at least 8 times.

Likely root causes:

- action router lacks negative memory for same error signature;
- acceptance criteria rewards local improvement, not final progress;
- prompts include previous attempts but do not convert them into actionable constraints;
- no explicit budget-aware stopping rule per action/error pair.

## L2. Missing Verusage-Specific Proof-Plan Transfer

Symptom: cross-model disagreement where one model verifies cheaply and another fails expensively.

Evidence: `top_100_cross_model_disagreements.csv` contains many files where a successful run uses far fewer tokens than failed models.

Likely root causes:

- successful proof structure is stored only as raw patch/log files;
- retrieval is generic, not project-family/lemma-graph aware;
- prompts replay too much code and too little distilled proof plan.

## L3. Context Is Too Broad For Some Families

Symptom: AC liveness prompts include whole flattened code and generic vstd examples; single calls can cost 40k-60k input tokens.

Likely root causes:

- no project-family context profile;
- helper lemmas are not indexed as a graph of premise/conclusion patterns;
- previous attempts are included as raw prose rather than compact state deltas.

## L4. Local Acceptance Can Increase Global Burden

Symptom: accepted local repair can convert a postcondition failure into a persistent assertion failure.

Likely root causes:

- acceptance checks target error-count reduction rather than downstream proof obligation complexity;
- no penalty for creating an assertion that becomes the repeated target;
- no explicit anti-regression metric on number and type of remaining errors.

## L5. Action Priors Are Not Family-Specific Enough

Evidence:

- `postcondition_repair` is often useful, but can create assertion loops.
- `add_trigger_assert`, `nonlinear_arithmetic`, and `bit_vector_reasoning` are frequent with low success marks in several summaries.
- `seqsetmap` is repeatedly selected for OS linked-list helpers.

Likely root causes:

- action priors are mostly error-type driven;
- task family, function name, lemma names, and prior successful patterns are underused.


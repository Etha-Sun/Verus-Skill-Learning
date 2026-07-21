# infogain rag reference for proof rationale reward

## Metadata

- project: `verus_self_evolving`
- kind: `literature`
- created_at: `2026-07-04T10:32:29`
- status: `complete`

## Scope

Connect InfoGain-RAG's Document Information Gain (DIG) idea to the July 4,
2026 Kexin meeting proposal:

```text
P(gt_proof | trajectory_t, artifact) - P(gt_proof | trajectory_t)
```

where `artifact` can be a counterexample-like debug rationale, a proof-repair
skill, or a sampled skill selected from the current skill memory.

## Sources

| source | link | why it matters |
|---|---|---|
| InfoGain-RAG: Boosting Retrieval-Augmented Generation via Document Information Gain-based Reranking and Filtering | https://arxiv.org/html/2509.12765v1 | Defines Document Information Gain as the confidence difference for generating the ground-truth answer with vs. without an added document; this is the closest direct analogue for scoring whether a rationale/skill helps predict the final proof. |

## Method Patterns

### 1. Confidence-difference reward

InfoGain-RAG scores a retrieved document by how much it changes the model's
confidence in the correct answer:

```text
DIG(document; query)
  = confidence(answer | query, document)
    - confidence(answer | query)
```

Our direct proof-agent analogue is:

```text
IG(artifact; trajectory_t)
  = score_T(gt_proof | trajectory_t, artifact)
    - score_T(gt_proof | trajectory_t)
```

Mapping:

| InfoGain-RAG | VeruSAGE self-evolving agent |
|---|---|
| query | trajectory prefix `trajectory_t` |
| retrieved document | candidate rationale / counterexample / skill |
| ground-truth answer | final verified proof `gt_proof` |
| LLM confidence | teacher-forced proof likelihood or normalized logprob |
| DIG | proof information gain of the artifact |

This turns Kexin's meeting formula into a concrete offline scoring contract: a
candidate artifact is useful if it increases the scoring model's likelihood of
the known final proof conditioned on the same partial trajectory.

### 2. Length-bias handling is essential

The paper explicitly notes that naively multiplying token probabilities has
length bias and that treating all answer tokens equally is weak. They mitigate
this with smoothing and token-importance weighting.

For Verus proofs this problem is more severe because final proofs are long and
syntactically structured. Candidate scoring should therefore avoid raw sequence
probability. Safer variants:

- average logprob over proof tokens;
- sliding-window normalized logprob;
- first-N proof-token or first-N proof-line score;
- score only changed proof spans after the trajectory prefix;
- line-level/chunk-level aggregation, then compare deltas;
- report sensitivity across at least two scoring definitions.

### 3. Positive / zero / negative artifact categories

InfoGain-RAG uses DIG to separate documents into helpful, neutral, and harmful
groups. This maps naturally to proof artifacts:

| category | VeruSAGE interpretation |
|---|---|
| positive IG | rationale/skill makes the final proof more likely; candidate for promotion |
| near-zero IG | irrelevant or already-known hint; likely not worth injecting |
| negative IG | misleading rationale/skill; should be filtered or demoted |

This gives a non-human-only rule source: rules/skills can be proposed by an LLM,
but promotion depends on measured information gain against held-out trajectory
prefixes and final proofs.

### 4. Reranker analogue

InfoGain-RAG trains a reranker with two objectives:

- classify whether an item has positive utility;
- rank useful items above less useful or harmful items.

Our analogue is a skill/rationale selector:

```text
P(sampled_skill | skills, trajectory_t)
```

The selector can be trained or tuned to:

- prefer skills with positive proof-IG on development prefixes;
- avoid skills with negative proof-IG;
- rank multiple candidate rationales/skills for the same trajectory state;
- remain plug-and-play before the expensive Verus live rerun.

## Takeaways For This Project

1. The new experiment should be framed as **information-gain-scored proof
   rationale/skill evolution**, not only repetition avoidance.

2. The first prototype should be an offline probe:

   ```text
   information_gain_reward_probe
   ```

   Minimal contract:

   - choose verified traces;
   - slice trajectory prefixes `(1)`, `(1,2,3)`, etc.;
   - extract the final verified proof as `gt_proof`;
   - generate candidate artifacts:
     - generic rationale;
     - trace-derived rationale;
     - irrelevant control;
     - motif/TLA-specific skill when applicable;
   - compute normalized teacher-forced logprob gain;
   - test whether trace-derived or motif-aware artifacts separate from controls.

3. If the score has signal, use it as a cheap promotion criterion for evolving
   skill memory before live Verus reruns.

4. If the score is flat/noisy, return to the lower-risk non-blocking steering
   path and treat information gain only as an analysis metric.

5. This paper is useful rhetorically because it supports the principle that
   "useful context" should be measured by downstream generation confidence, not
   semantic similarity or human intuition alone.

## Gaps / Risks

1. Ground-truth proofs are not unique. A likelihood gain may reward stylistic
   similarity to the known proof instead of semantic proof usefulness.

2. Final proof text must never be leaked into deployed prompts or held-out eval
   agents. It is only an offline scoring target.

3. Proof length makes the confidence estimator fragile; at least one normalized
   and one chunked score should be reported.

4. The reward is only a proxy. Final claims still need verifier-backed live
   reruns or held-out replay showing solved-rate/token-cost improvements.

5. Skill evolution can still overfit if candidate generation, scoring, and final
   reporting all use the same tasks. The evaluation contract must split by task
   and ideally stress cross-project or cross-model transfer.

## Next Step

Create an `experiments` entry for `information_gain_reward_probe` and implement
a small local run on 20-50 verified traces before committing to a full
self-evolving loop.

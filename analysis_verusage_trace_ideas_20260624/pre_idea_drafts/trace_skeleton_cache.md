# Pre-Idea Draft: Trace-Distilled Proof Skeleton Cache

## Two-Sentence Pitch

Mine successful Verusage traces into compact proof skeletons keyed by verifier error, project family, target function, nearby lemma names, and proof-shape. At repair time, retrieve the skeleton before sending another full-context LLM prompt, so the model sees the actual proof route rather than rediscovering it through repeated failed attempts.

## Hidden Assumptions

- Successful traces contain reusable proof structure, not only exact patches.
- Skeleton retrieval by project/error/lemma graph is more useful than raw token-similar vstd examples.
- The cache can be split to avoid leakage when evaluating model generalization.

## Strongest Rejection Case

The cache may collapse into exact-task memorization. If so, it is useful operationally for known Verusage instances but not defensible as a capability improvement.

## Cheapest Falsification

Offline:

1. Extract skeletons from successful traces.
2. For heldout failed traces, test whether the target's needed action/lemma/witness appears in the retrieved top-k skeletons.
3. Compare against generic token-similarity retrieval and raw previous-attempt inclusion.

Minimal online:

- Run 20-50 high-token failed `AC/NR/OS` tasks with skeleton hints and compare verified rate plus total tokens.

## Promotion Verdict

Promote, but only together with leakage-safe splits and a repetition gate.


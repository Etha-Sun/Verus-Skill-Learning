# Fold over concatenated sequences

## Scope

- Consult when: Goal is fold over concatenation equals concatenation of folds
- Consult when: Induction on second sequence or an existing split lemma is feasible
- Consult when: Accumulator concatenation is associative/append-like
- Not for: Fold operator is not associative or append-like
- Not for: Sequence split/decomposition lemmas are unavailable

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** Both address the same concatenated-fold goal. One needs compatible prefix/last decomposition; the other an installed split lemma and compatible accumulator formulation. If both are available, the source does not establish a unique best route or require both.

<a id="seq-fold-concat-induction-second"></a>
- [seq-fold-concat-induction-second](sequence-fold-concat-equality--seq-fold-concat-induction-second.md): Concatenated fold with prefix/last decomposition.
  - When: Direct concatenated-fold proof fails and the recursive fold has usable prefix/last decomposition with an append-like accumulator.
  - Avoid: Incompatible accumulator operation or unavailable decomposition relationship.

<a id="seq-fold-concat-split-lemma-helper"></a>
- [seq-fold-concat-split-lemma-helper](sequence-fold-concat-equality--seq-fold-concat-split-lemma-helper.md): Same concatenated-fold goal with an installed split lemma.
  - When: An installed split lemma matches the concatenation boundary and the accumulator-plus-empty formulation is compatible.
  - Avoid: No matching split lemma or incompatible accumulator formulation.

Read: `python3 reference_read.py sequence-fold-concat-equality --rules ID [ID ...]`

Whole reference: `python3 reference_read.py sequence-fold-concat-equality --full` or [sequence-fold-concat-equality--full.md](sequence-fold-concat-equality--full.md).

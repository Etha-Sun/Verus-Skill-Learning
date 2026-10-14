# Fold over concatenated sequences

## Scope

- Consult when: Goal is fold over concatenation equals concatenation of folds
- Consult when: Induction on second sequence or an existing split lemma is feasible
- Consult when: Accumulator concatenation is associative/append-like
- Not for: Fold operator is not associative or append-like
- Not for: Sequence split/decomposition lemmas are unavailable

## Rules

- [Fold over sequence concatenation: induct on the second sequence and use concatenation associativity](#seq-fold-concat-induction-second)
- [Alternative concatenated-fold route: existing split lemma plus a helper for a nonempty initial accumulator](#seq-fold-concat-split-lemma-helper)

<a id="seq-fold-concat-induction-second"></a>
## Fold over sequence concatenation: induct on the second sequence and use concatenation associativity

Source cards: card-063

**Trigger:** A proof obligation requires showing that a left fold over the concatenation of two sequences equals the concatenation of the two separate folds, and a direct assertion or unfolding does not close the proof. **Action:** Introduce a proof-only helper that performs induction on the length of the second sequence. In the base case, establish that the second sequence is empty and the combined sequence equals the first sequence. In the inductive case, decompose both folds through the sequence without its last element and the last element, apply the induction hypothesis to the shorter sequence, and close the remaining equality with associativity of sequence concatenation. Use existing library lemmas for the suffix and last-element relationships where available. **Why:** The fold definition recurses by removing the last element, so an induction aligned with that structure supplies the necessary recursive equality, while concatenation associativity handles the accumulator combination. **Validate:** Run Verus after each helper addition and correct any parse, type, or scope diagnostics; ensure the target lemma body invokes the helper and both Verus and the proof-only safety comparison pass. **Avoid when:** The fold operator is not associative or not append-like for the accumulator, or the sequence decomposition relationship involving the last element and prefix is not available in the relevant library.

<a id="seq-fold-concat-split-lemma-helper"></a>
## Alternative concatenated-fold route: existing split lemma plus a helper for a nonempty initial accumulator

Source cards: card-064

**Trigger:** A proof obligation about folding a concatenated sequence can be approached by splitting the concatenated sequence at the boundary between the two original parts. **Action:** Search the sequence library for an existing split lemma that folds the suffix from an accumulator. Prove a small helper stating that folding a sequence from a nonempty initial accumulator equals that accumulator concatenated with folding from the empty accumulator. Apply the split lemma with the first sequence length, identify the resulting subranges with the original arguments using extensional equality, and then invoke the helper to close the target obligation. **Why:** This avoids manual induction and leverages an already-proved distribution property for folding over a split sequence; the helper reduces the remaining gap to associativity of accumulator concatenation. **Validate:** Run Verus after adding the helper and rewrite steps, fix any natural-number-to-integer casts or empty-sequence type annotations, and confirm both Verus and the proof-only safety comparison pass. **Avoid when:** The library split lemma is unavailable, or the accumulator operation is not compatible with the helper's accumulator-plus-empty formulation.

- Distinguish from [finite-set-fold-cardinality-induction](finite-set-fold-cardinality-induction.md): Finite-set fold uses source-set cardinality; sequence fold uses sequence length or split boundary.

- Distinguish from [specialized-fold-bound-lemmas](specialized-fold-bound-lemmas.md): Specialized-bound route creates concrete recursive lemmas for element bounds; concat route proves distribution over sequence append.

- Related [finite-set-fold-cardinality-induction](finite-set-fold-cardinality-induction.md): Finite-set fold uses source-set cardinality; sequence fold uses sequence length or split boundary.

- Related [specialized-fold-bound-lemmas](specialized-fold-bound-lemmas.md): Specialized-bound route creates concrete recursive lemmas for element bounds; concat route proves distribution over sequence append.

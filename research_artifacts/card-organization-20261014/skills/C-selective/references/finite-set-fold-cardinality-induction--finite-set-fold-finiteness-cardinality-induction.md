# Finite-set fold proofs by cardinality induction

## Scope

- Consult when: Goal concerns a fold over a finite set, such as finiteness or equality to an image
- Consult when: Direct assertion or generic fold lemma does not close the goal
- Consult when: Source-set cardinality provides a decreasing measure
- Not for: Fold is not defined by finite cardinality recursion
- Not for: Direct library lemma already closes the goal

<a id="finite-set-fold-finiteness-cardinality-induction"></a>
## Finite-set fold result finiteness by cardinality induction

Source cards: card-017

**Trigger:** A proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure.

**Action:** Use induction on the cardinality of the finite input set. In the zero-cardinality case, show the folded result equals the empty set, so it is finite. In the nonzero-cardinality case, choose an element, assert that removing it strictly lowers the cardinality, recursively prove finiteness for the result over the remaining set, and assert that the full fold equals the recursive result with the image of the chosen element inserted. Conclude finiteness through the fact that inserting into a finite set preserves finiteness. Either add a recursive proof helper and call it from the required function, or if allowed add the decreasing clause and reason directly inside the required function.

**Why:** The recursive equality mirrors the recursive definition of the fold, so the full result is exposed as an insert over a smaller fold. Induction on a strictly decreasing cardinality gives termination and transfers the finiteness property step by step.

**Validate:** Rerun Verus until every function verifies with no errors, then run the proof-safety comparison and expect a zero exit and no differences.

**Avoid when:** The folding operator does not have a decreasing cardinality argument, or the empty and nonempty unfoldings do not produce the equality needed to transfer finiteness.

- Distinguish from [sequence-fold-concat-equality](sequence-fold-concat-equality.md): Sequence fold route concerns concatenated sequences and split/induction over second sequence; this route uses finite-set cardinality induction.

- Related [sequence-fold-concat-equality](sequence-fold-concat-equality.md): Finite-set fold uses source-set cardinality; sequence fold uses sequence length or split boundary. Use this family when the goal is a finite-set fold property, not concatenation distribution over sequences.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Try direct-existing-lemma-bridge first when an installed or already-declared lemma/trait contract has matching conclusion and premises; finite-set cardinality induction is for when direct library lemma does not close the fold goal and built-in set reasoning is needed.

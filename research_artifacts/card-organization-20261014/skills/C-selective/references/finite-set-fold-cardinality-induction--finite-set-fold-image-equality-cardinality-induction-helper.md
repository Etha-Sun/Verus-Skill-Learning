# Finite-set fold proofs by cardinality induction

## Scope

- Consult when: Goal concerns a fold over a finite set, such as finiteness or equality to an image
- Consult when: Direct assertion or generic fold lemma does not close the goal
- Consult when: Source-set cardinality provides a decreasing measure
- Not for: Fold is not defined by finite cardinality recursion
- Not for: Direct library lemma already closes the goal

<a id="finite-set-fold-image-equality-cardinality-induction-helper"></a>
## Finite-set fold equality to an image by cardinality induction with a proof-only helper

Source cards: card-048

**Trigger:** A proof function has a missing body and a postcondition that a fold-computed set equals the image of a finite source set under a supplied function; the fold is defined by recursion on finite cardinality.

**Action:** Prove the equality by induction on the finite source-set cardinality. To preserve the original externally visible proof function, add a proof-only helper with the same requires and ensures, and give the helper a decreasing measure based on the source-set length; have the original proof function call the helper. In the zero-length case, show the source set is empty, the fold returns the empty accumulator, and the image of the empty set is empty. In the nonzero case, choose an element, remove it, establish the remainder is finite and smaller, recurse, unfold the fold definition one step, and prove that rebuilding the source set and mapping over the rebuilt set matches the image of the remainder with the chosen element's image inserted. Prefer direct set extensionality, closed built-in set definitions, and any installed broadcast facts rather than guessed named helper lemmas.

**Why:** Induction on cardinality follows the fold recursion structure. A helper carries the termination measure without changing the original proof function's signature or termination clauses. Direct built-in set reasoning discharges the small set identities, whereas a prior attempt using guessed named set-library lemmas failed because those names were not in scope in this toolchain.

**Validate:** Re-run Verus; the prior postcondition failure should become two or three verified functions with zero errors, depending on whether a helper is introduced. Run the proof-only safety comparison afterward; it should pass when only proof-only bodies are changed.

**Avoid when:** The source set is not required finite or the fold is not defined by finite-cardinality recursion. Avoid altering the original proof function's signature, requires, ensures, or termination clauses when a proof-only helper can carry the needed decrease. Do not rely on guessed helper-lemma names without confirming the installed library exports.

- Distinguish from [sequence-fold-concat-equality](sequence-fold-concat-equality.md): Sequence fold route concerns concatenated sequences and split/induction over second sequence; this route uses finite-set cardinality induction.

- Related [sequence-fold-concat-equality](sequence-fold-concat-equality.md): Finite-set fold uses source-set cardinality; sequence fold uses sequence length or split boundary. Use this family when the goal is a finite-set fold property, not concatenation distribution over sequences.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Try direct-existing-lemma-bridge first when an installed or already-declared lemma/trait contract has matching conclusion and premises; finite-set cardinality induction is for when direct library lemma does not close the fold goal and built-in set reasoning is needed.

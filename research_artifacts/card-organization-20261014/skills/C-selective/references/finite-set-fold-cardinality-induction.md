# Finite-set fold proofs by cardinality induction

## Scope

- Consult when: Goal concerns a fold over a finite set, such as finiteness or equality to an image
- Consult when: Direct assertion or generic fold lemma does not close the goal
- Consult when: Source-set cardinality provides a decreasing measure
- Not for: Fold is not defined by finite cardinality recursion
- Not for: Direct library lemma already closes the goal

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** Select by the requested conclusion: result finiteness versus equality to the mapped source set. Sharing cardinality induction does not make the conclusions interchangeable.

<a id="finite-set-fold-finiteness-cardinality-induction"></a>
- [finite-set-fold-finiteness-cardinality-induction](finite-set-fold-cardinality-induction--finite-set-fold-finiteness-cardinality-induction.md): Finiteness of a folded set.
  - When: A fold over a finite input set must produce a finite set.
  - Avoid: No decreasing cardinality argument or unsuitable empty/nonempty fold equalities.

<a id="finite-set-fold-image-equality-cardinality-induction-helper"></a>
- [finite-set-fold-image-equality-cardinality-induction-helper](finite-set-fold-cardinality-induction--finite-set-fold-image-equality-cardinality-induction-helper.md): Folded set equals a set image.
  - When: A finite-cardinality recursive fold must equal the image of its finite source set.
  - Avoid: Source finiteness or finite-cardinality recursion is absent.

Read: `python3 reference_read.py finite-set-fold-cardinality-induction --rules ID [ID ...]`

Whole reference: `python3 reference_read.py finite-set-fold-cardinality-induction --full` or [finite-set-fold-cardinality-induction--full.md](finite-set-fold-cardinality-induction--full.md).
